import { Extension } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    paragraphSpacing: {
      setParagraphMargin: (which: 'top' | 'right' | 'bottom' | 'left', value: string) => ReturnType
      setParagraphTextIndent: (value: string) => ReturnType
      resetParagraphSpacing: () => ReturnType
    }
  }
}

/**
 * Adds margin + first-line-indent attributes to block-level nodes
 * (paragraph / heading / list item / task item / blockquote) so users can
 * tweak spacing per-paragraph the way Word & Google Docs allow.
 *
 * Values are CSS strings (e.g. ``"24px"`` or ``""`` to clear).
 *
 * The names purposefully mirror the JSON keys produced by the backend
 * DOCX importer (marginTop / marginBottom / marginLeft / marginRight /
 * textIndent) so a round-trip through the server preserves them.
 */
export const ParagraphSpacing = Extension.create({
  name: 'paragraphSpacing',

  addOptions() {
    return {
      types: ['paragraph', 'heading', 'listItem', 'taskItem', 'blockquote'] as string[],
    }
  },

  addGlobalAttributes() {
    const attrs: Record<string, any> = {}
    const fields: Array<['marginTop' | 'marginRight' | 'marginBottom' | 'marginLeft' | 'textIndent', string]> = [
      ['marginTop', 'margin-top'],
      ['marginRight', 'margin-right'],
      ['marginBottom', 'margin-bottom'],
      ['marginLeft', 'margin-left'],
      ['textIndent', 'text-indent'],
    ]

    for (const [key, css] of fields) {
      attrs[key] = {
        default: '',
        parseHTML: (el: HTMLElement) => (el.style as any)[css.replace(/-(.)/g, (_m, c) => c.toUpperCase())] || '',
        renderHTML: (a: Record<string, string>) => {
          const v = a[key]
          if (!v) return {}
          return { style: `${css}: ${v}` }
        },
      }
    }

    return [
      {
        types: this.options.types,
        attributes: attrs,
      },
    ]
  },

  addCommands() {
    return {
      setParagraphMargin:
        (which: 'top' | 'right' | 'bottom' | 'left', value: string) =>
        ({ commands }) => {
          const key = `margin${which.charAt(0).toUpperCase()}${which.slice(1)}`
          return this.options.types.every((t: string) =>
            commands.updateAttributes(t, { [key]: value }),
          )
        },

      setParagraphTextIndent:
        (value: string) =>
        ({ commands }) =>
          this.options.types.every((t: string) =>
            commands.updateAttributes(t, { textIndent: value }),
          ),

      resetParagraphSpacing:
        () =>
        ({ commands }) =>
          this.options.types.every((t: string) =>
            commands.resetAttributes(t, [
              'marginTop',
              'marginRight',
              'marginBottom',
              'marginLeft',
              'textIndent',
            ]),
          ),
    }
  },
})
