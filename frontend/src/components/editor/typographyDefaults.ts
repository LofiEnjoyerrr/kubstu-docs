/**
 * Shared typography defaults for the Tiptap editor and the DOCX
 * importer/exporter. The editor's CSS, the DOCX export's docDefaults and
 * the backend's import logic must agree on these values so a given amount
 * of text occupies the same number of pages everywhere.
 *
 * Keep in sync with:
 *   - TiptapEditor.vue           (CSS .tiptap-editor / .tiptap-mini)
 *   - backend/docs/docx_importer.py  (DEFAULT_FONT_* / DEFAULT_LINE_HEIGHT)
 */

export const DEFAULT_FONT_FAMILY = 'Times New Roman'
export const DEFAULT_FONT_SIZE_PT = 14
export const DEFAULT_LINE_HEIGHT = 1.15

/** Word stores font sizes in half-points (sz = 28 ⇒ 14pt). */
export const DEFAULT_FONT_SIZE_HALF_POINTS = DEFAULT_FONT_SIZE_PT * 2

/** Word stores line spacing as twentieths of a line (240 = single). */
export const DEFAULT_LINE_SPACING_TWIPS = Math.round(240 * DEFAULT_LINE_HEIGHT)
