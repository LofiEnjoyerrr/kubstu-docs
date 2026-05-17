import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import type { Editor } from '@tiptap/core'

export interface CommentMark {
  id: number
  from: number
  to: number
  color: string
}

const key = new PluginKey<CommentMark[]>('commentHighlights')

export const CommentHighlights = Extension.create({
  name: 'commentHighlights',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key,
        state: {
          init(): CommentMark[] { return [] },
          apply(tr, marks): CommentMark[] {
            const meta = tr.getMeta(key) as CommentMark[] | undefined
            return meta !== undefined ? meta : marks
          },
        },
        props: {
          decorations(state) {
            const marks: CommentMark[] = key.getState(state) ?? []
            const decos: Decoration[] = []
            const maxPos = state.doc.content.size

            for (const m of marks) {
              const from = Math.max(0, Math.min(m.from, maxPos))
              const to = Math.max(0, Math.min(m.to, maxPos))
              if (from >= to) continue
              decos.push(
                Decoration.inline(from, to, {
                  style: `background:${m.color}33; border-bottom: 2px solid ${m.color};`,
                  class: 'comment-highlight',
                  'data-comment-id': String(m.id),
                }),
              )
            }

            return DecorationSet.create(state.doc, decos)
          },
        },
      }),
    ]
  },
})

export function setCommentMarks(editor: Editor, marks: CommentMark[]) {
  const { tr } = editor.state
  editor.view.dispatch(tr.setMeta(key, marks))
}
