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
 * Block-level node. Renders as a thin separator in the editor and as a
 * proper ``<w:br w:type="page"/>`` when exported. Optionally carries
 * ``restartNumbering`` + ``numberStart`` so the document can reset the
 * page-number sequence at this break (matching the Word "Section break,
 * next page" feature with "Restart at" page numbering).
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
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-page-break': 'true',
        class: 'page-break',
        contenteditable: 'false',
      }),
      ['span', { class: 'page-break-label' }, 'Page break'],
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
