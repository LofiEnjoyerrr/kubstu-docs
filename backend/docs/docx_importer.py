"""
DOCX → Tiptap JSON converter that honors direct formatting.

Why we wrote our own:
    The original frontend used mammoth.js, which deliberately drops "explicit"
    Word formatting like ``<w:jc w:val="center"/>``. The result is that text
    centered or justified directly on a paragraph (not via a named style) was
    coming through as plain left-aligned text. This module reads the OOXML
    directly and produces a Tiptap-compatible JSON document that preserves
    alignment, indentation, fonts, colors, spacing, lists, tables, images,
    headers, footers and page settings.

Conventions (kept consistent with the Tiptap schema used by the frontend):
    * Lengths the editor uses for paragraph margins / indents / spacing are
      stored as **CSS pixel strings** (e.g. ``"96px"``) because every Tiptap
      extension we currently render uses pixels.
    * Font sizes go through as ``"<n>px"`` strings on the ``textStyle`` mark
      so the existing FontSize extension picks them up.
    * Line spacing is a unitless multiplier on the paragraph's ``lineHeight``
      attribute (matches the LineHeight extension shipped on the client).
    * Tables follow Tiptap's default table schema (``table`` → ``tableRow`` →
      ``tableCell`` / ``tableHeader``).
"""

from __future__ import annotations

import io
import os
import re
import uuid
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


# Shared typography defaults. Must match the frontend's
# ``components/editor/typographyDefaults.ts`` so that the editor and the DOCX
# render the same amount of text per page when no explicit run formatting
# is present. We intentionally do NOT pin a default line height — the editor's
# CSS uses ``line-height: normal`` and we only emit an explicit ``lineHeight``
# attribute for paragraphs whose source DOCX requested a non-auto line rule.
DEFAULT_FONT_FAMILY = 'Times New Roman'
DEFAULT_FONT_SIZE_PT = 14.0


# ─── XML namespaces ───────────────────────────────────────────────────────────

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
PIC_NS = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
WP_NS = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'

NS = {'w': W_NS, 'r': R_NS, 'a': A_NS, 'pic': PIC_NS, 'wp': WP_NS}

W = f'{{{W_NS}}}'
R = f'{{{R_NS}}}'
A = f'{{{A_NS}}}'
PIC = f'{{{PIC_NS}}}'
WP = f'{{{WP_NS}}}'


# ─── unit conversion ──────────────────────────────────────────────────────────

# 1 inch = 1440 twips = 96 px (web) = 914400 EMUs
TWIPS_PER_PX = 15  # 1440 / 96
EMU_PER_PX = 9525  # 914400 / 96


def twips_to_px(twips: str | int | None) -> int | None:
    if twips is None:
        return None
    try:
        n = int(float(twips))
    except (TypeError, ValueError):
        return None
    return round(n / TWIPS_PER_PX)


def emu_to_px(emu: str | int | None) -> int | None:
    if emu is None:
        return None
    try:
        n = int(float(emu))
    except (TypeError, ValueError):
        return None
    return round(n / EMU_PER_PX)


def halfpt_to_pt(halfpt: str | int | None) -> float | None:
    """Word font sizes are in half-points. The editor now stores sizes in
    points (``"12pt"``) so the toolbar dropdown's number matches what
    appears in the exported DOCX. Returns the value as a float since
    Word allows half-point increments (e.g. 10.5pt)."""
    if halfpt is None:
        return None
    try:
        n = float(halfpt)
    except (TypeError, ValueError):
        return None
    return n / 2


# ─── helpers ──────────────────────────────────────────────────────────────────

def qn(local_name: str, ns: str = W_NS) -> str:
    """Build a fully-qualified XML tag name."""
    return f'{{{ns}}}{local_name}'


def first(el: ET.Element | None, *path: str) -> ET.Element | None:
    """Walk a path of child element names, returning None if anything is missing."""
    cur = el
    for name in path:
        if cur is None:
            return None
        cur = cur.find(qn(name))
    return cur


def attr(el: ET.Element | None, name: str, ns: str = W_NS) -> str | None:
    if el is None:
        return None
    return el.get(qn(name, ns))


def color_to_hex(value: str | None) -> str | None:
    """Word colors are 6-digit hex without #. Filter out 'auto' / blanks."""
    if not value or value.lower() == 'auto':
        return None
    if re.fullmatch(r'[0-9a-fA-F]{6}', value):
        return f'#{value.upper()}'
    return None


WORD_HIGHLIGHT_COLORS: dict[str, str] = {
    'yellow': '#fff59d',
    'green': '#a5d6a7',
    'cyan': '#80deea',
    'magenta': '#f48fb1',
    'blue': '#90caf9',
    'red': '#ef9a9a',
    'darkBlue': '#1565c0',
    'darkCyan': '#00838f',
    'darkGreen': '#2e7d32',
    'darkMagenta': '#ad1457',
    'darkRed': '#b71c1c',
    'darkYellow': '#f9a825',
    'darkGray': '#616161',
    'lightGray': '#cfd8dc',
    'black': '#000000',
    'white': '#ffffff',
}


# ─── numbering parser ────────────────────────────────────────────────────────

class NumberingDef:
    """Holds the level → bullet/ordered mapping for one ``numId``."""

    def __init__(self) -> None:
        # level (int) → 'bullet' | 'ordered'
        self.levels: dict[int, str] = {}


class NumberingRegistry:
    """Lookup table built from word/numbering.xml — maps each numId to its style."""

    def __init__(self) -> None:
        self._defs: dict[str, NumberingDef] = {}

    @classmethod
    def from_xml(cls, xml: bytes | None) -> 'NumberingRegistry':
        reg = cls()
        if not xml:
            return reg
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return reg

        # abstractNumId → NumberingDef
        abstract: dict[str, NumberingDef] = {}
        for an in root.findall(qn('abstractNum')):
            an_id = an.get(qn('abstractNumId'))
            if an_id is None:
                continue
            d = NumberingDef()
            for lvl in an.findall(qn('lvl')):
                ilvl = lvl.get(qn('ilvl'))
                fmt_el = lvl.find(qn('numFmt'))
                fmt = fmt_el.get(qn('val')) if fmt_el is not None else None
                if ilvl is not None:
                    d.levels[int(ilvl)] = 'bullet' if fmt == 'bullet' else 'ordered'
            abstract[an_id] = d

        # num → references one abstractNum
        for num in root.findall(qn('num')):
            num_id = num.get(qn('numId'))
            ab_ref = num.find(qn('abstractNumId'))
            if num_id is None or ab_ref is None:
                continue
            ab_id = ab_ref.get(qn('val'))
            if ab_id in abstract:
                reg._defs[num_id] = abstract[ab_id]
        return reg

    def kind_for(self, num_id: str | None, ilvl: int) -> str | None:
        if num_id is None:
            return None
        d = self._defs.get(num_id)
        if not d:
            return None
        return d.levels.get(ilvl) or d.levels.get(0)


# ─── styles parser ───────────────────────────────────────────────────────────

class StyleDef:
    def __init__(self) -> None:
        self.heading_level: int | None = None
        self.alignment: str | None = None
        self.is_list_paragraph: bool = False
        # Run-level defaults from this style. Font size is stored as a
        # point value (matches what the editor's dropdown displays and what
        # Word writes out in DOCX).
        self.font_family: str | None = None
        self.font_size_pt: float | None = None
        self.bold: bool = False
        self.italic: bool = False


class DocDefaults:
    """Snapshot of ``<w:docDefaults>`` — applied to runs that lack explicit
    font / size so the editor renders the same density of text the source
    DOCX had. Values are stored in human units (point + name)."""

    def __init__(self) -> None:
        self.font_family: str | None = None
        self.font_size_pt: float | None = None


class StyleRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, StyleDef] = {}
        self.doc_defaults = DocDefaults()

    @classmethod
    def from_xml(cls, xml: bytes | None) -> 'StyleRegistry':
        reg = cls()
        if not xml:
            return reg
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return reg
        # docDefaults — global run / paragraph fallback.
        dd = root.find(qn('docDefaults'))
        if dd is not None:
            rpr_default = first(dd, 'rPrDefault', 'rPr')
            if rpr_default is not None:
                rfont = rpr_default.find(qn('rFonts'))
                if rfont is not None:
                    reg.doc_defaults.font_family = (
                        rfont.get(qn('ascii'))
                        or rfont.get(qn('hAnsi'))
                        or rfont.get(qn('cs'))
                    )
                sz = rpr_default.find(qn('sz'))
                if sz is not None:
                    reg.doc_defaults.font_size_pt = halfpt_to_pt(sz.get(qn('val')))
        for st in root.findall(qn('style')):
            sid = st.get(qn('styleId'))
            if not sid:
                continue
            d = StyleDef()
            # heading-N style ids
            name_el = st.find(qn('name'))
            name = name_el.get(qn('val')) if name_el is not None else ''
            m = re.match(r'^heading\s+(\d)$', name, re.IGNORECASE)
            if m:
                d.heading_level = int(m.group(1))
            if name.lower() == 'list paragraph':
                d.is_list_paragraph = True
            ppr = st.find(qn('pPr'))
            if ppr is not None:
                jc = ppr.find(qn('jc'))
                if jc is not None:
                    d.alignment = jc.get(qn('val'))
            rpr = st.find(qn('rPr'))
            if rpr is not None:
                rfont = rpr.find(qn('rFonts'))
                if rfont is not None:
                    d.font_family = (
                        rfont.get(qn('ascii'))
                        or rfont.get(qn('hAnsi'))
                        or rfont.get(qn('cs'))
                    )
                sz = rpr.find(qn('sz'))
                if sz is not None:
                    d.font_size_pt = halfpt_to_pt(sz.get(qn('val')))
                if rpr.find(qn('b')) is not None:
                    d.bold = True
                if rpr.find(qn('i')) is not None:
                    d.italic = True
            reg._by_id[sid] = d
        return reg

    def get(self, sid: str | None) -> StyleDef | None:
        if not sid:
            return None
        return self._by_id.get(sid)


# ─── main converter ──────────────────────────────────────────────────────────

class DocxConverter:
    """
    Converts a DOCX file (path / file-like / bytes) to a Tiptap JSON document.

    The constructor only stores the inputs; call :meth:`convert` to do the
    actual parsing. Doing it lazily keeps unit tests trivial: instantiate, run.
    """

    def __init__(
        self,
        docx_source: str | bytes | io.IOBase,
        *,
        document_pk: int,
        media_subdir: str | None = None,
    ) -> None:
        self.source = docx_source
        self.document_pk = document_pk
        self.media_subdir = media_subdir or f'docs/{document_pk}/images'

        # Populated by convert()
        self.zip: zipfile.ZipFile | None = None
        self.rels: dict[str, str] = {}
        self.styles = StyleRegistry()
        self.numbering = NumberingRegistry()
        # rId → media path on the server (e.g. "/media/docs/4/images/abcdef.png")
        self._image_url_by_rid: dict[str, str] = {}
        # Becomes True the moment we encounter ANY pagination signal — a hard
        # page break, a ``lastRenderedPageBreak`` rendered by Word, a section
        # break, or a PAGE / NUMPAGES field in a header / footer. Surfaces
        # via the ``has_pagination`` key in convert()'s result so the API
        # layer can flip ``show_page_numbers`` on.
        self._has_pagination = False

    # ------------------------------------------------------------------ public

    def convert(self) -> dict[str, Any]:
        """
        Returns a dict like::

            {
              "content":         { "type": "doc", "content": [...] },
              "page_layout":     {page_width, margin_top, ...},
              "header_content":  { "type": "doc", "content": [...] }  | None,
              "footer_content":  { "type": "doc", "content": [...] }  | None,
            }
        """
        if isinstance(self.source, (bytes, bytearray)):
            self.zip = zipfile.ZipFile(io.BytesIO(self.source))
        else:
            self.zip = zipfile.ZipFile(self.source)

        try:
            self._load_relationships()
            self._load_styles_and_numbering()
            self._upload_images()

            doc_xml = self.zip.read('word/document.xml')
            root = ET.fromstring(doc_xml)
            body = root.find(qn('body'))
            assert body is not None, 'DOCX without <w:body>'

            content = self._build_body(body)
            page_layout = self._build_page_layout(body)
            header_content, footer_content = self._build_header_footer()

            return {
                'content': {'type': 'doc', 'content': content},
                'page_layout': page_layout,
                'header_content': header_content,
                'footer_content': footer_content,
                'has_pagination': self._has_pagination,
            }
        finally:
            if self.zip:
                self.zip.close()

    # -------------------------------------------------------------- relationships

    def _load_relationships(self) -> None:
        try:
            data = self.zip.read('word/_rels/document.xml.rels')  # type: ignore[union-attr]
        except KeyError:
            return
        root = ET.fromstring(data)
        # Namespace is the package relationships ns, not the openxml r: ns.
        for rel in root:
            rid = rel.get('Id')
            target = rel.get('Target')
            if rid and target:
                self.rels[rid] = target

    def _load_styles_and_numbering(self) -> None:
        try:
            self.styles = StyleRegistry.from_xml(self.zip.read('word/styles.xml'))  # type: ignore[union-attr]
        except KeyError:
            pass
        try:
            self.numbering = NumberingRegistry.from_xml(self.zip.read('word/numbering.xml'))  # type: ignore[union-attr]
        except KeyError:
            pass

    # ------------------------------------------------------------ image upload

    def _upload_images(self) -> None:
        """Pull every embedded image out of the DOCX and stash it in MEDIA_ROOT."""
        for rid, target in self.rels.items():
            if not target:
                continue
            path = target if target.startswith('word/') else f'word/{target.lstrip("/")}'
            try:
                blob = self.zip.read(path)  # type: ignore[union-attr]
            except KeyError:
                continue
            ext = os.path.splitext(target)[1].lower() or '.png'
            if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}:
                continue
            filename = f'{uuid.uuid4().hex}{ext}'
            saved = default_storage.save(
                f'{self.media_subdir}/{filename}',
                ContentFile(blob),
            )
            self._image_url_by_rid[rid] = settings.MEDIA_URL + saved

    # ---------------------------------------------------------- page settings

    def _build_page_layout(self, body: ET.Element) -> dict[str, int]:
        """
        Read page size/margins from the document's section properties.

        OOXML stores intermediate sections as ``<w:sectPr>`` inside a
        paragraph's ``<w:pPr>`` (that paragraph closes the section), and the
        FINAL section as a top-level ``<w:sectPr>`` on the body. The page
        size and margins for the layout settings come from the body-final
        sectPr; the numbering start, however, must come from the FIRST
        section's properties so the document's "start at" setting matches
        page 1's number.
        """
        layout = {
            'page_width': 816,
            'page_height': 1056,
            'margin_top': 96,
            'margin_right': 96,
            'margin_bottom': 96,
            'margin_left': 96,
        }
        final_sect = body.find(qn('sectPr'))
        if final_sect is not None:
            pgsz = final_sect.find(qn('pgSz'))
            if pgsz is not None:
                w = twips_to_px(pgsz.get(qn('w')))
                h = twips_to_px(pgsz.get(qn('h')))
                if w:
                    layout['page_width'] = w
                if h:
                    layout['page_height'] = h
            pgmar = final_sect.find(qn('pgMar'))
            if pgmar is not None:
                for src, dst in (
                    ('top', 'margin_top'),
                    ('right', 'margin_right'),
                    ('bottom', 'margin_bottom'),
                    ('left', 'margin_left'),
                ):
                    v = twips_to_px(pgmar.get(qn(src)))
                    if v is not None:
                        layout[dst] = v

        # Find the FIRST section's pgNumType: the first intermediate sectPr if
        # any, else the body-final sectPr.
        first_sect = None
        for p in body.findall(qn('p')):
            ppr = p.find(qn('pPr'))
            if ppr is None:
                continue
            inner = ppr.find(qn('sectPr'))
            if inner is not None:
                first_sect = inner
                break
        if first_sect is None:
            first_sect = final_sect
        if first_sect is not None:
            pg_num = first_sect.find(qn('pgNumType'))
            if pg_num is not None:
                start = pg_num.get(qn('start'))
                if start is not None:
                    try:
                        layout['page_number_start'] = int(start)
                    except ValueError:
                        pass
        return layout

    # ----------------------------------------------------- header/footer parse

    def _build_header_footer(self) -> tuple[dict | None, dict | None]:
        """Parse the first available header and footer, if any."""
        header: dict | None = None
        footer: dict | None = None
        for rid, target in self.rels.items():
            if not target:
                continue
            kind = None
            if 'header' in target.lower():
                kind = 'header'
            elif 'footer' in target.lower():
                kind = 'footer'
            if not kind:
                continue
            path = target if target.startswith('word/') else f'word/{target.lstrip("/")}'
            try:
                xml = self.zip.read(path)  # type: ignore[union-attr]
            except KeyError:
                continue
            try:
                hf_root = ET.fromstring(xml)
            except ET.ParseError:
                continue
            # A PAGE / NUMPAGES field anywhere in a header / footer means the
            # source DOCX intends to display page numbers — flag pagination.
            if self._contains_page_field(hf_root):
                self._has_pagination = True
            content = self._build_body(hf_root)
            doc = {'type': 'doc', 'content': content or [self._empty_paragraph()]}
            if kind == 'header' and header is None:
                header = doc
            elif kind == 'footer' and footer is None:
                footer = doc
        return header, footer

    @staticmethod
    def _contains_page_field(root: ET.Element) -> bool:
        """True if the subtree contains a Word PAGE / NUMPAGES field — either
        a simple field (``<w:fldSimple w:instr="PAGE"/>``) or a complex one
        (``<w:instrText>PAGE</w:instrText>``)."""
        for el in root.iter():
            if el.tag == qn('fldSimple'):
                instr = el.get(qn('instr')) or ''
                if 'PAGE' in instr.upper():
                    return True
            elif el.tag == qn('instrText'):
                txt = (el.text or '').upper()
                if 'PAGE' in txt or 'NUMPAGES' in txt:
                    return True
            elif el.tag == qn('pgNum'):
                return True
        return False

    # ------------------------------------------------------------ body parse

    def _build_body(self, body: ET.Element) -> list[dict]:
        """
        Walk a ``<w:body>`` (or ``<w:hdr>``/``<w:ftr>``) and produce a list of
        Tiptap block nodes. Consecutive list-paragraphs collapse into a single
        ``bulletList`` / ``orderedList`` so the editor renders them as one list.

        Word marks the end of a section either with an in-body ``<w:sectPr>``
        (intermediate section) or the body-final ``<w:sectPr>`` (last section).
        Each intermediate section produces a ``sectionBreak`` node so the
        editor can render it as a visual page boundary AND keep its
        independent page-number sequence.
        """
        out: list[dict] = []
        list_buffer: list[tuple[str, dict, int]] = []  # (kind, paragraph_node, level)

        def flush_list() -> None:
            nonlocal list_buffer
            if not list_buffer:
                return
            # Group by kind — we may have a bullet block followed by an ordered.
            i = 0
            while i < len(list_buffer):
                kind = list_buffer[i][0]
                j = i
                while j < len(list_buffer) and list_buffer[j][0] == kind:
                    j += 1
                items = []
                for _, p_node, _level in list_buffer[i:j]:
                    items.append({'type': 'listItem', 'content': [p_node]})
                out.append({
                    'type': 'bulletList' if kind == 'bullet' else 'orderedList',
                    'content': items,
                })
                i = j
            list_buffer = []

        for child in body:
            tag = child.tag
            if tag == qn('p'):
                kind_level = self._paragraph_list_kind(child)
                if kind_level is not None:
                    kind, level = kind_level
                    p_node = self._build_paragraph(child, in_list=True)
                    list_buffer.append((kind, p_node, level))
                    continue
                flush_list()
                # _build_paragraph_blocks may emit multiple block nodes
                # when the paragraph contains inline images / page breaks
                # (block-level in our schema).
                for block in self._build_paragraph_blocks(child):
                    out.append(block)
                # An intermediate <w:sectPr> nested in a paragraph's pPr marks
                # the END of a section. Convert it to a sectionBreak node and
                # remember that the source DOCX paginates.
                ppr = child.find(qn('pPr'))
                if ppr is not None and ppr.find(qn('sectPr')) is not None:
                    sect_pr = ppr.find(qn('sectPr'))
                    out.append(self._section_break_from_sect_pr(sect_pr))
                    self._has_pagination = True
            elif tag == qn('tbl'):
                flush_list()
                out.append(self._build_table(child))
            else:
                # The body-final sectPr lives at the top level — we skip it
                # here (the layout/page setup parser handles it separately).
                continue
        flush_list()

        if not out:
            out.append(self._empty_paragraph())
        return out

    @staticmethod
    def _section_break_from_sect_pr(sect_pr: ET.Element | None) -> dict:
        """
        Build a ``sectionBreak`` node from a ``<w:sectPr>``. Honors
        ``<w:pgNumType w:start="N"/>`` for restart numbering.
        """
        attrs: dict[str, Any] = {}
        if sect_pr is not None:
            pg_num = sect_pr.find(qn('pgNumType'))
            if pg_num is not None:
                start = pg_num.get(qn('start'))
                if start is not None:
                    try:
                        attrs['restartNumbering'] = True
                        attrs['numberStart'] = int(start)
                    except ValueError:
                        pass
        if not attrs:
            # No explicit restart — default to "continue numbering".
            attrs = {'restartNumbering': False, 'numberStart': 1}
        return {'type': 'sectionBreak', 'attrs': attrs}

    @staticmethod
    def _empty_paragraph() -> dict:
        return {'type': 'paragraph'}

    # -------------------------------------------------------- list classification

    def _paragraph_list_kind(self, p: ET.Element) -> tuple[str, int] | None:
        """Return ('bullet'|'ordered', level) if this <w:p> belongs to a list."""
        ppr = p.find(qn('pPr'))
        if ppr is None:
            return None
        num_pr = ppr.find(qn('numPr'))
        if num_pr is None:
            return None
        num_id_el = num_pr.find(qn('numId'))
        ilvl_el = num_pr.find(qn('ilvl'))
        num_id = num_id_el.get(qn('val')) if num_id_el is not None else None
        ilvl = int(ilvl_el.get(qn('val'))) if (ilvl_el is not None and ilvl_el.get(qn('val'))) else 0
        kind = self.numbering.kind_for(num_id, ilvl) or 'bullet'
        return kind, ilvl

    # -------------------------------------------------------------- paragraph

    # Nodes that are inline-encoded inside a Word paragraph but are
    # actually block-level in our Tiptap schema. When we find any of these
    # inside a ``<w:p>`` we have to split the paragraph at that point and
    # emit them as block-level siblings — otherwise ProseMirror's schema
    # silently filters them out on load (which is what caused imported
    # DOCX page breaks and images to disappear).
    _BLOCK_INLINE_TYPES: 'set[str]' = {'image', 'pageBreak'}

    def _build_paragraph_attrs(self, p: ET.Element, *, in_list: bool = False) -> 'tuple[str, dict[str, Any]]':
        """Extract ``(node_type, attrs)`` for the paragraph or heading."""
        ppr = p.find(qn('pPr'))
        attrs: dict[str, Any] = {}

        # Style → maybe heading
        heading_level: int | None = None
        if ppr is not None:
            pstyle = ppr.find(qn('pStyle'))
            if pstyle is not None:
                sd = self.styles.get(pstyle.get(qn('val')))
                if sd and sd.heading_level:
                    heading_level = sd.heading_level

        # Alignment (jc)
        alignment = None
        if ppr is not None:
            jc = ppr.find(qn('jc'))
            if jc is not None:
                v = jc.get(qn('val'))
                alignment = {'both': 'justify', 'distribute': 'justify'}.get(v, v)

        # Indents + first-line indent
        margin_left = margin_right = first_line = None
        if ppr is not None:
            ind = ppr.find(qn('ind'))
            if ind is not None:
                margin_left = twips_to_px(ind.get(qn('left')) or ind.get(qn('start')))
                margin_right = twips_to_px(ind.get(qn('right')) or ind.get(qn('end')))
                first_line = twips_to_px(ind.get(qn('firstLine')))
                hanging = twips_to_px(ind.get(qn('hanging')))
                if hanging:
                    # Hanging indent is the inverse of firstLine: drop it as negative.
                    first_line = -hanging

        # Spacing
        margin_top = margin_bottom = None
        line_height: str | None = None
        if ppr is not None:
            sp = ppr.find(qn('spacing'))
            if sp is not None:
                margin_top = twips_to_px(sp.get(qn('before')))
                margin_bottom = twips_to_px(sp.get(qn('after')))
                line = sp.get(qn('line'))
                rule = sp.get(qn('lineRule'))
                if line:
                    try:
                        n = int(float(line))
                    except ValueError:
                        n = 0
                    if n:
                        if rule in (None, 'auto'):
                            # ``auto`` line spacing is encoded in 240ths of
                            # single spacing: 240 = single (1.0), 360 = 1.5,
                            # 480 = double, 276 = Word's 1.15 default. We
                            # previously dropped this value because there's
                            # no CSS analogue to Word's "natural metrics"
                            # and a multiplier slightly shifts page breaks
                            # vs. the source DOCX. That trade-off was wrong:
                            # losing the user's explicit 1.5/double spacing
                            # produces a visibly wrong document, while the
                            # page-drift is small. So we now emit the
                            # multiplier for every non-single value, and
                            # leave 240 (= 1.0 = the CSS default) unset.
                            if n != 240:
                                line_height = f'{round(n / 240.0, 3)}'
                            else:
                                line_height = None
                        else:
                            # ``exact`` / ``atLeast`` — value is in twips,
                            # not 240ths. Convert to a multiplier against
                            # the run font size when possible; otherwise
                            # leave it unset.
                            pt = n / 20.0
                            line_height = f'{round(pt / DEFAULT_FONT_SIZE_PT, 3)}'

        # Assemble Tiptap attrs (only when set)
        if alignment in {'left', 'center', 'right', 'justify'}:
            attrs['textAlign'] = alignment
        if margin_top is not None:
            attrs['marginTop'] = f'{margin_top}px'
        if margin_bottom is not None:
            attrs['marginBottom'] = f'{margin_bottom}px'
        if margin_left is not None and not in_list:
            # When inside a list the indentation comes from the list itself.
            attrs['marginLeft'] = f'{margin_left}px'
        if margin_right is not None:
            attrs['marginRight'] = f'{margin_right}px'
        if first_line is not None:
            attrs['textIndent'] = f'{first_line}px'
        if line_height:
            attrs['lineHeight'] = line_height

        node_type = 'heading' if heading_level else 'paragraph'
        if heading_level:
            attrs['level'] = heading_level

        return node_type, attrs

    def _build_paragraph_blocks(self, p: ET.Element, *, in_list: bool = False) -> 'list[dict]':
        """
        Build the block-level nodes for a single Word paragraph.

        A ``<w:p>`` in Word may contain block-level content (images, page
        breaks) inlined among its runs. The Tiptap schema treats those as
        block nodes, so when ProseMirror parses a paragraph that lists
        them as ``content`` it silently drops them. To keep that data we
        split the paragraph at each block-level inline and emit the
        blocks as siblings — exactly the result one would expect in
        Tiptap / Google Docs.
        """
        node_type, attrs = self._build_paragraph_attrs(p, in_list=in_list)
        inline_items = self._build_inline(p)

        blocks: list[dict] = []
        current_inline: list[dict] = []

        def emit_paragraph() -> None:
            nonlocal current_inline
            node: dict[str, Any] = {'type': node_type}
            if attrs:
                node['attrs'] = dict(attrs)
            if current_inline:
                node['content'] = current_inline
            blocks.append(node)
            current_inline = []

        for item in inline_items:
            if item.get('type') in self._BLOCK_INLINE_TYPES:
                if current_inline:
                    emit_paragraph()
                # Marks attached during hyperlink traversal are not valid
                # on block-level nodes — strip them on the way out.
                item.pop('marks', None)
                blocks.append(item)
            else:
                current_inline.append(item)

        if current_inline:
            emit_paragraph()
        elif not blocks:
            # Word kept an empty paragraph here — preserve it.
            emit_paragraph()

        return blocks

    def _build_paragraph(self, p: ET.Element, *, in_list: bool = False) -> dict:
        """
        Returns a single paragraph node. Used by the list builder, where
        each list item expects exactly one paragraph. Block-level inline
        items inside a list paragraph are simply dropped — Word lists
        with embedded images or page breaks are rare and we keep the
        text content intact.
        """
        node_type, attrs = self._build_paragraph_attrs(p, in_list=in_list)
        inline_content = [
            n for n in self._build_inline(p)
            if n.get('type') not in self._BLOCK_INLINE_TYPES
        ]

        node: dict[str, Any] = {'type': node_type}
        if attrs:
            node['attrs'] = attrs
        if inline_content:
            node['content'] = inline_content
        return node

    # --------------------------------------------------------- inline content

    def _build_inline(self, p: ET.Element) -> list[dict]:
        """Walk a paragraph's children, producing Tiptap inline nodes."""
        out: list[dict] = []
        for child in p:
            tag = child.tag
            if tag == qn('r'):
                out.extend(self._build_run(child))
            elif tag == qn('hyperlink'):
                href = child.get(qn('id', R_NS))
                href_url = self.rels.get(href, '') if href else ''
                if not href_url and child.get(qn('anchor')):
                    href_url = '#' + child.get(qn('anchor'))
                link_mark = (
                    {'type': 'link', 'attrs': {'href': href_url}}
                    if href_url else None
                )
                for r in child.findall(qn('r')):
                    runs = self._build_run(r)
                    if link_mark:
                        for tr in runs:
                            tr.setdefault('marks', []).append(link_mark)
                    out.extend(runs)
            elif tag == qn('proofErr') or tag == qn('bookmarkStart') or tag == qn('bookmarkEnd'):
                continue
            elif tag in (
                qn('commentRangeStart'),
                qn('commentRangeEnd'),
                qn('commentReference'),
            ):
                # Word comments are dropped on import. The editor has its
                # own comment system (``CommentHighlights``) keyed by doc
                # positions, so blindly converting Word-side annotations
                # would attach them to the wrong ranges after the
                # paragraph-and-run flattening done above. Strip every
                # marker the comment subsystem uses (range start/end on
                # paragraph children, plus the reference markers inside
                # runs — see ``_build_run``) so nothing leaks through.
                continue
        # Tiptap dislikes runs without text — drop empties.
        return [n for n in out if n.get('text') or n.get('type') in {'image', 'hardBreak', 'pageBreak'}]

    def _build_run(self, r: ET.Element) -> list[dict]:
        rpr = r.find(qn('rPr'))

        # rStyle is the named-run-style reference; merge defaults in.
        style_defaults = None
        if rpr is not None:
            rstyle = rpr.find(qn('rStyle'))
            if rstyle is not None:
                style_defaults = self.styles.get(rstyle.get(qn('val')))

        marks = self._marks_for_rpr(rpr, style_defaults)
        out: list[dict] = []

        for child in r:
            tag = child.tag
            if tag == qn('t'):
                txt = child.text or ''
                if not txt:
                    continue
                node: dict[str, Any] = {'type': 'text', 'text': txt}
                if marks:
                    node['marks'] = [dict(m) for m in marks]
                out.append(node)
            elif tag == qn('br'):
                br_type = child.get(qn('type'))
                if br_type == 'page':
                    out.append({'type': 'pageBreak'})
                    self._has_pagination = True
                else:
                    out.append({'type': 'hardBreak'})
            elif tag == qn('lastRenderedPageBreak'):
                # Word writes this element wherever IT laid out a page break
                # during its last save — a layout cache, not user intent.
                # Word almost always emits one alongside every real
                # ``<w:br w:type="page"/>``, so honoring both produces two
                # page breaks in the editor for a single break in the source.
                # We DO let it bump the "has pagination" flag so the editor
                # turns on page numbering, but we leave the break itself to
                # the auto-paginator (which re-flows text page-by-page using
                # the same page size Word uses).
                self._has_pagination = True
            elif tag == qn('tab'):
                # Tiptap doesn't have a tab node; render as 4 spaces.
                out.append({'type': 'text', 'text': ' '})
            elif tag == qn('drawing'):
                img = self._image_from_drawing(child)
                if img:
                    out.append(img)
            elif tag == qn('pict'):
                img = self._image_from_pict(child)
                if img:
                    out.append(img)
            elif tag == qn('commentReference'):
                # Comments are stripped on import — see ``_build_inline``.
                continue
        return out

    def _marks_for_rpr(
        self,
        rpr: ET.Element | None,
        defaults: StyleDef | None,
    ) -> list[dict]:
        marks: list[dict] = []

        def has(tag: str) -> bool:
            if rpr is None:
                return False
            el = rpr.find(qn(tag))
            if el is None:
                return False
            val = el.get(qn('val'))
            # In OOXML, missing val means "true". Explicit "0"/"false" = off.
            return val not in {'0', 'false', 'off'}

        if has('b') or (defaults and defaults.bold):
            marks.append({'type': 'bold'})
        if has('i') or (defaults and defaults.italic):
            marks.append({'type': 'italic'})
        if has('u'):
            marks.append({'type': 'underline'})
        if has('strike') or has('dstrike'):
            marks.append({'type': 'strike'})

        # Sub/superscript
        if rpr is not None:
            va = rpr.find(qn('vertAlign'))
            if va is not None:
                v = va.get(qn('val'))
                if v == 'superscript':
                    marks.append({'type': 'superscript'})
                elif v == 'subscript':
                    marks.append({'type': 'subscript'})

        # textStyle: font, size, color
        ts: dict[str, str] = {}
        font_family = None
        font_size_pt: float | None = None
        color_hex = None

        if rpr is not None:
            rfont = rpr.find(qn('rFonts'))
            if rfont is not None:
                font_family = (
                    rfont.get(qn('ascii'))
                    or rfont.get(qn('hAnsi'))
                    or rfont.get(qn('cs'))
                )
            sz = rpr.find(qn('sz'))
            if sz is not None:
                font_size_pt = halfpt_to_pt(sz.get(qn('val')))
            col = rpr.find(qn('color'))
            if col is not None:
                color_hex = color_to_hex(col.get(qn('val')))

        if not font_family and defaults:
            font_family = defaults.font_family
        if not font_size_pt and defaults:
            font_size_pt = defaults.font_size_pt

        # Final fallback — docDefaults from styles.xml, then the shared
        # editor default. Apply explicitly so the editor renders the text
        # with the same metrics Word used (which is what makes
        # text-per-page actually match the source DOCX).
        dd = self.styles.doc_defaults
        if not font_family:
            font_family = dd.font_family or DEFAULT_FONT_FAMILY
        if not font_size_pt:
            font_size_pt = dd.font_size_pt or DEFAULT_FONT_SIZE_PT

        if font_family:
            ts['fontFamily'] = font_family
        if font_size_pt:
            # Emit as integer pt when possible — matches the toolbar
            # dropdown values exactly (which are whole-number sizes).
            rounded = round(font_size_pt)
            if abs(font_size_pt - rounded) < 0.01:
                ts['fontSize'] = f'{rounded}pt'
            else:
                ts['fontSize'] = f'{font_size_pt:g}pt'
        if color_hex:
            ts['color'] = color_hex
        if ts:
            marks.append({'type': 'textStyle', 'attrs': ts})

        # Highlight
        if rpr is not None:
            hl = rpr.find(qn('highlight'))
            if hl is not None:
                v = hl.get(qn('val'))
                if v and v != 'none':
                    marks.append(
                        {'type': 'highlight', 'attrs': {'color': WORD_HIGHLIGHT_COLORS.get(v, v)}},
                    )
            # Shading also frequently carries highlight color.
            shd = rpr.find(qn('shd'))
            if shd is not None:
                fill = shd.get(qn('fill'))
                if fill and fill.lower() != 'auto':
                    marks.append(
                        {'type': 'highlight', 'attrs': {'color': f'#{fill.upper()}'}},
                    )
        return marks

    # ------------------------------------------------------------------ image

    def _image_from_drawing(self, drawing: ET.Element) -> dict | None:
        # Look for <a:blip r:embed="rIdN"/> anywhere under the drawing.
        blip = drawing.find(f'.//{A}blip')
        if blip is None:
            return None
        rid = blip.get(qn('embed', R_NS)) or blip.get(qn('link', R_NS))
        if not rid:
            return None
        url = self._image_url_by_rid.get(rid)
        if not url:
            return None

        # Size from <wp:extent cx=".." cy="..">
        extent = drawing.find(f'.//{WP}extent')
        attrs: dict[str, Any] = {'src': url}
        if extent is not None:
            w = emu_to_px(extent.get('cx'))
            h = emu_to_px(extent.get('cy'))
            if w:
                attrs['width'] = w
            if h:
                attrs['height'] = h
        return {'type': 'image', 'attrs': attrs}

    def _image_from_pict(self, pict: ET.Element) -> dict | None:
        # Legacy VML images. Hunt for a v:imagedata id=.
        for el in pict.iter():
            if el.tag.endswith('}imagedata'):
                rid = el.get(qn('id', R_NS))
                if rid and rid in self._image_url_by_rid:
                    return {'type': 'image', 'attrs': {'src': self._image_url_by_rid[rid]}}
        return None

    # ------------------------------------------------------------------ table

    def _build_table(self, tbl: ET.Element) -> dict:
        rows: list[dict] = []
        for tr in tbl.findall(qn('tr')):
            cells: list[dict] = []
            for tc in tr.findall(qn('tc')):
                cell_content: list[dict] = []
                for child in tc:
                    tag = child.tag
                    if tag == qn('p'):
                        # Same block-extraction as the body so embedded
                        # images survive inside table cells.
                        cell_content.extend(self._build_paragraph_blocks(child))
                    elif tag == qn('tbl'):
                        cell_content.append(self._build_table(child))
                if not cell_content:
                    cell_content = [self._empty_paragraph()]
                cell_attrs: dict[str, Any] = {}
                tc_pr = tc.find(qn('tcPr'))
                if tc_pr is not None:
                    grid_span = tc_pr.find(qn('gridSpan'))
                    if grid_span is not None and grid_span.get(qn('val')):
                        cell_attrs['colspan'] = int(grid_span.get(qn('val')))
                cells.append({
                    'type': 'tableCell',
                    'attrs': cell_attrs or {'colspan': 1, 'rowspan': 1, 'colwidth': None},
                    'content': cell_content,
                })
            if cells:
                rows.append({'type': 'tableRow', 'content': cells})
        if not rows:
            rows = [{
                'type': 'tableRow',
                'content': [{
                    'type': 'tableCell',
                    'attrs': {'colspan': 1, 'rowspan': 1, 'colwidth': None},
                    'content': [self._empty_paragraph()],
                }],
            }]
        return {'type': 'table', 'content': rows}


# ─── thin public helper ──────────────────────────────────────────────────────

def docx_to_tiptap(
    docx_source: str | bytes | io.IOBase,
    *,
    document_pk: int,
) -> dict[str, Any]:
    """Convenience wrapper: parse a DOCX and return the Tiptap payload."""
    return DocxConverter(docx_source, document_pk=document_pk).convert()
