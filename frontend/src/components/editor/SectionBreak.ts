import { Node, mergeAttributes } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    sectionBreak: {
      /**
       * Insert a section break. A section break behaves like a page break
       * visually, but it also opens a new "section" whose page-number
       * sequence is independent from the previous one.
       */
      insertSectionBreak: (opts?: { restartNumbering?: boolean; numberStart?: number }) => ReturnType
    }
  }
}

/**
 * Block-level node — Word-style "section break (next page)". Always begins
 * a new page; by default it also restarts page numbering at 1. The editor
 * renders it with a more prominent gap than a regular page break so the
 * user can tell sections apart.
 */
export const SectionBreak = Node.create({
  name: 'sectionBreak',

  group: 'block',

  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      restartNumbering: {
        default: true,
        parseHTML: el => (el as HTMLElement).dataset.restartNumbering !== 'false',
        renderHTML: a => ({ 'data-restart-numbering': a.restartNumbering ? 'true' : 'false' }),
      },
      numberStart: {
        default: 1,
        parseHTML: el => {
          const v = (el as HTMLElement).dataset.numberStart
          const n = v ? parseInt(v, 10) : NaN
          return isNaN(n) ? 1 : n
        },
        renderHTML: a => ({ 'data-number-start': String(a.numberStart ?? 1) }),
      },
    }
  },

  parseHTML() {
    return [
      { tag: 'div[data-section-break]' },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-section-break': 'true',
        class: 'section-break',
        contenteditable: 'false',
      }),
      ['div', { class: 'page-break-paper-end' }],
      ['div', { class: 'page-break-gap section-break-gap' }, ['span', { class: 'section-break-label' }, 'Section break']],
      ['div', { class: 'page-break-paper-start' }],
    ]
  },

  addCommands() {
    return {
      insertSectionBreak:
        (opts = {}) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: {
              restartNumbering: opts.restartNumbering ?? true,
              numberStart: opts.numberStart ?? 1,
            },
          }),
    }
  },
})
