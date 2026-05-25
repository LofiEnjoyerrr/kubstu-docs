"""
Tests for the DOCX importer's PAGE / NUMPAGES field handling and the
per-section ``sectionBreak`` properties used by the editor + exporter.

These tests build the minimum DOCX structure each assertion needs — no
real .docx fixture files — so they stay hermetic and quick.
"""

from __future__ import annotations

import io
import textwrap
import zipfile

import pytest

from docs.docx_importer import DocxConverter


# ─── helpers ────────────────────────────────────────────────────────────────

_BASE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rIdF" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
    '</Relationships>'
)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
    '</Types>'
)


def _build_docx(document_xml: str, footer_xml: str | None = None) -> bytes:
    """Pack a one-part document (+ optional footer) into a DOCX archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CONTENT_TYPES)
        z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        z.writestr('word/document.xml', document_xml)
        if footer_xml is not None:
            z.writestr('word/_rels/document.xml.rels', _BASE_RELS)
            z.writestr('word/footer1.xml', footer_xml)
    return buf.getvalue()


def _wrap_doc(body_inner: str) -> str:
    return textwrap.dedent(f'''\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <w:body>{body_inner}</w:body>
        </w:document>
    ''')


def _wrap_footer(body_inner: str) -> str:
    return textwrap.dedent(f'''\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
               xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          {body_inner}
        </w:ftr>
    ''')


def _convert(document_xml: str, footer_xml: str | None = None) -> dict:
    return DocxConverter(_build_docx(document_xml, footer_xml), document_pk=1).convert()


def _footer_inline_nodes(result: dict) -> list[dict]:
    """Pull the inline children of the footer's first paragraph."""
    assert result['footer_content'] is not None
    para = result['footer_content']['content'][0]
    return para.get('content', [])


# ─── PAGE field handling ────────────────────────────────────────────────────

def test_simple_page_field_emits_pageNumber_node():
    """``<w:fldSimple w:instr="PAGE">`` becomes a pageNumber inline node."""
    footer = _wrap_footer(
        '<w:p><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    inlines = _footer_inline_nodes(result)
    assert inlines == [{'type': 'pageNumber', 'attrs': {'kind': 'number'}}]


def test_simple_numpages_field_emits_count_kind():
    footer = _wrap_footer(
        '<w:p><w:fldSimple w:instr="NUMPAGES"><w:r><w:t>10</w:t></w:r></w:fldSimple></w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    inlines = _footer_inline_nodes(result)
    assert inlines == [{'type': 'pageNumber', 'attrs': {'kind': 'count'}}]


def test_complex_page_field_strips_cached_value_and_emits_pageNumber():
    """
    The PAGE field's cached display ``<w:t>1</w:t>`` must NOT survive
    as literal text — that's what caused the "every page shows 1" bug
    on round-trip.
    """
    footer = _wrap_footer(
        '<w:p>'
        r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        r'<w:r><w:instrText>PAGE   \* MERGEFORMAT</w:instrText></w:r>'
        r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        r'<w:r><w:t>7</w:t></w:r>'
        r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    inlines = _footer_inline_nodes(result)
    assert inlines == [{'type': 'pageNumber', 'attrs': {'kind': 'number'}}]


def test_complex_field_text_outside_separator_block_is_preserved():
    """Text BEFORE a complex field shouldn't be swallowed by the skip logic."""
    footer = _wrap_footer(
        '<w:p>'
        '<w:r><w:t>Стр. </w:t></w:r>'
        r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        r'<w:r><w:instrText>PAGE</w:instrText></w:r>'
        r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        r'<w:r><w:t>1</w:t></w:r>'
        r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '<w:r><w:t> из </w:t></w:r>'
        r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        r'<w:r><w:instrText>NUMPAGES</w:instrText></w:r>'
        r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    inlines = _footer_inline_nodes(result)
    types = [n.get('type') for n in inlines]
    # Pattern: "Стр. " <pageNumber number> " из " <pageNumber count>
    assert types == ['text', 'pageNumber', 'text', 'pageNumber']
    assert inlines[0]['text'] == 'Стр. '
    assert inlines[1]['attrs']['kind'] == 'number'
    assert inlines[2]['text'] == ' из '
    assert inlines[3]['attrs']['kind'] == 'count'


def test_non_page_field_is_dropped_cleanly():
    """A field we don't handle (HYPERLINK) should not emit a pageNumber node."""
    footer = _wrap_footer(
        '<w:p>'
        r'<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        r'<w:r><w:instrText>HYPERLINK "https://example.com"</w:instrText></w:r>'
        r'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        r'<w:r><w:t>example</w:t></w:r>'
        r'<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    inlines = _footer_inline_nodes(result)
    pn_count = sum(1 for n in inlines if n.get('type') == 'pageNumber')
    assert pn_count == 0


# ─── sectionBreak properties ───────────────────────────────────────────────

def test_section_break_carries_next_section_properties_not_closed_section():
    """
    A ``<w:sectPr>`` in a paragraph's ``<w:pPr>`` describes the section
    being CLOSED — but a Tiptap ``sectionBreak`` describes the section
    being OPENED. The importer must look up the NEXT section's pgNumType.
    """
    # Section 1 ends with start=0; section 2 (body-final) has start=3.
    doc = _wrap_doc(
        '<w:p><w:pPr><w:sectPr>'
        '<w:pgNumType w:start="0"/>'
        '</w:sectPr></w:pPr></w:p>'
        '<w:p/>'
        '<w:sectPr><w:pgNumType w:start="3"/></w:sectPr>'
    )
    result = _convert(doc)

    section_breaks = [n for n in result['content']['content'] if n.get('type') == 'sectionBreak']
    assert len(section_breaks) == 1
    # The break carries section 2's start, not section 1's.
    assert section_breaks[0]['attrs']['numberStart'] == 3
    assert section_breaks[0]['attrs']['restartNumbering'] is True


def test_two_section_breaks_each_carry_their_opener_properties():
    """Three-section document like the user's KR file."""
    doc = _wrap_doc(
        '<w:p><w:pPr><w:sectPr>'
        '<w:pgNumType w:start="0"/>'
        '</w:sectPr></w:pPr></w:p>'
        '<w:p><w:pPr><w:sectPr>'
        '<w:pgNumType w:start="0"/>'
        '</w:sectPr></w:pPr></w:p>'
        '<w:p/>'
        '<w:sectPr><w:pgNumType w:start="3"/></w:sectPr>'
    )
    result = _convert(doc)

    section_breaks = [n for n in result['content']['content'] if n.get('type') == 'sectionBreak']
    assert len(section_breaks) == 2
    # break 1 opens section 2 (start=0); break 2 opens section 3 (start=3).
    assert [b['attrs']['numberStart'] for b in section_breaks] == [0, 3]


# ─── page layout ───────────────────────────────────────────────────────────

def test_page_number_start_read_from_first_intermediate_section():
    """``page_layout.page_number_start`` is the FIRST section's start."""
    doc = _wrap_doc(
        '<w:p><w:pPr><w:sectPr>'
        '<w:pgNumType w:start="5"/>'
        '</w:sectPr></w:pPr></w:p>'
        '<w:p/>'
        '<w:sectPr><w:pgNumType w:start="9"/></w:sectPr>'
    )
    result = _convert(doc)

    assert result['page_layout']['page_number_start'] == 5


def test_has_pagination_flag_set_when_footer_has_page_field():
    footer = _wrap_footer(
        '<w:p><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p>',
    )
    doc = _wrap_doc('<w:p/><w:sectPr/>')
    result = _convert(doc, footer)

    assert result['has_pagination'] is True


def test_no_pagination_flag_when_no_page_field_and_no_breaks():
    doc = _wrap_doc('<w:p><w:r><w:t>plain text</w:t></w:r></w:p><w:sectPr/>')
    result = _convert(doc)

    assert result['has_pagination'] is False
