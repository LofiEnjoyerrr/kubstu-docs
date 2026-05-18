import { Extension } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    lineHeight: {
      setLineHeight: (value: string) => ReturnType
      unsetLineHeight: () => ReturnType
    }
  }
}

/**
 * Adds a `lineHeight` attribute on every block node so the user can set
 * spacing per paragraph / heading the same way Word & Google Docs allow.
 *
 * Values are CSS line-height strings (`1`, `1.5`, `2`, …). The attribute is
 * applied as an inline style on the rendered element.
 */
export const LineHeight = Extension.create({
  name: 'lineHeight',

  addOptions() {
    return {
      types: ['heading', 'paragraph', 'listItem', 'taskItem'] as string[],
      defaultLineHeight: '',
    }
  },

  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          lineHeight: {
            default: this.options.defaultLineHeight,
            parseHTML: el => (el as HTMLElement).style.lineHeight || '',
            renderHTML: attrs => {
              if (!attrs.lineHeight) return {}
              return { style: `line-height: ${attrs.lineHeight}` }
            },
          },
        },
      },
    ]
  },

  addCommands() {
    return {
      setLineHeight: (value: string) => ({ commands }) =>
        this.options.types.every((t: string) =>
          commands.updateAttributes(t, { lineHeight: value }),
        ),
      unsetLineHeight: () => ({ commands }) =>
        this.options.types.every((t: string) =>
          commands.resetAttributes(t, 'lineHeight'),
        ),
    }
  },
})
