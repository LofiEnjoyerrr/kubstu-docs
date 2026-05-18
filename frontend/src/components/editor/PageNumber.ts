import { Node, mergeAttributes } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    pageNumber: {
      insertPageNumber: () => ReturnType
      insertPageCount: () => ReturnType
    }
  }
}

/**
 * Inline placeholder. In the editor it renders as a small chip whose
 * label is *recomputed by the page layout engine* in the document view —
 * the editor itself only stores the placeholder, never a baked-in number.
 *
 * Word equivalents:
 *     - kind="number" → ``<w:fldSimple w:instr="PAGE"/>``
 *     - kind="count"  → ``<w:fldSimple w:instr="NUMPAGES"/>``
 */
export const PageNumber = Node.create({
  name: 'pageNumber',

  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      kind: {
        default: 'number',
        parseHTML: el => (el as HTMLElement).dataset.kind ?? 'number',
        renderHTML: a => ({ 'data-kind': a.kind }),
      },
    }
  },

  parseHTML() {
    return [
      { tag: 'span[data-page-number]' },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    // Placeholder label — the document view rewrites this per-page.
    const label = (HTMLAttributes as Record<string, string>)['data-kind'] === 'count' ? '#/N' : '#'
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-page-number': 'true',
        class: 'page-number-chip',
        contenteditable: 'false',
      }),
      label,
    ]
  },

  addCommands() {
    return {
      insertPageNumber:
        () =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs: { kind: 'number' } }),
      insertPageCount:
        () =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs: { kind: 'count' } }),
    }
  },
})
