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
            // Explicit replacement (e.g. setComments call) always wins.
            const meta = tr.getMeta(key) as CommentMark[] | undefined
            if (meta !== undefined) return meta

            // No document change → positions are still valid.
            if (!tr.docChanged) return marks

            // Map every comment's boundaries through the transaction steps.
            // The range is INCLUSIVE at both edges: bias -1 on `from` and
            // bias +1 on `to` make text typed at either boundary stick to
            // the comment, so editing the highlighted text grows or shrinks
            // the highlight along with it. Deletions still pull the edges
            // inward, and once the range collapses the highlight is dropped.
            return marks
              .map(m => ({
                ...m,
                from: tr.mapping.map(m.from, -1),
                to:   tr.mapping.map(m.to,    1),
              }))
              .filter(m => m.from < m.to) // collapsed range → highlight gone
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

export function getCommentMarks(editor: Editor): CommentMark[] {
  return key.getState(editor.state) ?? []
}
