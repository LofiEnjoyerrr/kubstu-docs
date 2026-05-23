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
 * Line height is pinned to an explicit multiplier of 1.2 — both sides
 * support an exact line-height: the editor via CSS ``line-height: 1.2``,
 * and Word via ``<w:spacing line="336" lineRule="atLeast"/>`` where
 * 336 = 1.2 × 14pt × 20 twips/pt. ``atLeast`` (not ``exact``) so taller
 * inline content like images still gets the room it needs.
 *
 * Earlier defaults (``normal`` on the editor, no line spec in the export)
 * left both sides at the mercy of font-specific metrics, which Chrome and
 * Word resolve to noticeably different pixel heights for the same font.
 */

export const DEFAULT_FONT_FAMILY = 'Times New Roman'
export const DEFAULT_FONT_SIZE_PT = 14
export const DEFAULT_LINE_HEIGHT = 1.2

/** Word stores font sizes in half-points (sz = 28 ⇒ 14pt). */
export const DEFAULT_FONT_SIZE_HALF_POINTS = DEFAULT_FONT_SIZE_PT * 2

/**
 * Word line spacing in twips (1pt = 20 twips). Used with
 * ``lineRule="atLeast"`` in the export's docDefaults so every paragraph
 * without an explicit ``lineHeight`` lands on the same per-line pixel
 * count as the editor renders via ``line-height: 1.2``.
 */
export const DEFAULT_LINE_SPACING_TWIPS = Math.round(
  DEFAULT_LINE_HEIGHT * DEFAULT_FONT_SIZE_PT * 20,
)
