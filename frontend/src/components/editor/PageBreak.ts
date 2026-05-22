import { Node, mergeAttributes } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    pageBreak: {
      /** Insert a Word-style page break that visually starts a new page. */
      insertPageBreak: () => ReturnType
      /** Same as above but resets the page number sequence at this break. */
      insertPageBreakResetNumbering: (startAt?: number) => ReturnType
    }
  }
}

/**
 * Block-level node. Renders as a wide "between-pages" gap in the editor and
 * as a proper ``<w:br w:type="page"/>`` when exported. Optionally carries
 * ``restartNumbering`` + ``numberStart`` so the document can reset the
 * page-number sequence at this break.
 *
 * The actual chrome that makes the gap look like the bottom of one sheet
 * and the top of the next (paper edges, shadows, header/footer previews) is
 * rendered by the parent editor view using Vue — this node only commits the
 * skeleton DOM so ProseMirror can find/select it.
 */
export const PageBreak = Node.create({
  name: 'pageBreak',

  group: 'block',

  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      restartNumbering: {
        default: false,
        parseHTML: el => (el as HTMLElement).dataset.restartNumbering === 'true',
        renderHTML: a => (a.restartNumbering ? { 'data-restart-numbering': 'true' } : {}),
      },
      numberStart: {
        default: null,
        parseHTML: el => {
          const v = (el as HTMLElement).dataset.numberStart
          const n = v ? parseInt(v, 10) : NaN
          return isNaN(n) ? null : n
        },
        renderHTML: a => (a.numberStart != null ? { 'data-number-start': String(a.numberStart) } : {}),
      },
    }
  },

  parseHTML() {
    return [
      { tag: 'div[data-page-break]' },
      { tag: 'hr.page-break' },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    // The ``page-break-marker`` label visually announces that this is a
    // user-inserted (or DOCX-imported) page break, NOT a seam introduced by
    // the auto-paginator. AutoPagination's widget DOM has no marker, so the
    // two are visually distinct without needing extra selectors.
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-page-break': 'true',
        class: 'page-break manual-page-break',
        contenteditable: 'false',
      }),
      ['span', { class: 'page-break-marker' }, 'Разрыв страницы'],
      ['span', { class: 'page-break-page-label' }],
    ]
  },

  addCommands() {
    return {
      insertPageBreak:
        () =>
        ({ commands }) =>
          commands.insertContent({ type: this.name }),

      insertPageBreakResetNumbering:
        (startAt = 1) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { restartNumbering: true, numberStart: startAt },
          }),
    }
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Enter': () => this.editor.commands.insertPageBreak(),
    }
  },
})
