/**
 * Shared typography defaults for the Tiptap editor and the DOCX
 * importer/exporter. The editor's CSS, the DOCX export's docDefaults and
 * the backend's import logic must agree on these values so a given amount
 * of text occupies the same number of pages everywhere.
 *
 * Keep in sync with:
 *   - TiptapEditor.vue           (CSS .tiptap-editor / .tiptap-mini)
 *   - backend/docs/docx_importer.py  (DEFAULT_FONT_*)
 *
 * Line height is pinned to ``1.0`` — i.e. the line box height equals the
 * font size, the tightest setting that still renders all glyphs. This
 * matches what Word does when ``<w:spacing line="280" lineRule="exact"/>``
 * is applied (= 14pt × 20 twips). With ``lineRule="exact"`` Word does NOT
 * pad lines up to the font's natural ascent + descent + line gap (which
 * for Times New Roman 14pt would add ~3pt of leading and cut the page
 * capacity by ~15%), so the editor and the exported DOCX both fit the
 * same number of lines on a page.
 *
 * Why this changed: earlier multipliers (``normal`` and then ``1.2``)
 * gave the editor way fewer lines per page than Word ended up producing,
 * so a multi-page editor session would collapse to two pages in the
 * exported file. Pinning both sides to ``1.0`` / ``lineRule="exact"`` is
 * the only way to make the per-page text density actually match.
 */

export const DEFAULT_FONT_FAMILY = 'Times New Roman'
export const DEFAULT_FONT_SIZE_PT = 14
export const DEFAULT_LINE_HEIGHT = 1.0

/** Word stores font sizes in half-points (sz = 28 ⇒ 14pt). */
export const DEFAULT_FONT_SIZE_HALF_POINTS = DEFAULT_FONT_SIZE_PT * 2

/**
 * Word line spacing in twips (1pt = 20 twips). Used with
 * ``lineRule="exact"`` in the export's docDefaults so every paragraph
 * without an explicit ``lineHeight`` lands on the same per-line pixel
 * count as the editor renders via ``line-height: 1``.
 */
export const DEFAULT_LINE_SPACING_TWIPS = Math.round(
  DEFAULT_LINE_HEIGHT * DEFAULT_FONT_SIZE_PT * 20,
)
