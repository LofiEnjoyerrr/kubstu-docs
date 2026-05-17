import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import type { Editor } from '@tiptap/core'

export interface RemoteCursor {
  user_id: number | null
  username: string
  color: string
  from: number
  to: number
}

type CursorMap = Map<number | string, RemoteCursor>

const key = new PluginKey<CursorMap>('remoteCursors')

function buildCursorEl(c: RemoteCursor): HTMLElement {
  const wrap = document.createElement('span')
  wrap.style.cssText = 'position:relative;pointer-events:none;'

  const caret = document.createElement('span')
  caret.style.cssText = [
    'position:absolute',
    'top:-2px',
    'bottom:-2px',
    'left:-1px',
    'width:2px',
    `background:${c.color}`,
    'pointer-events:none',
    'border-radius:1px',
  ].join(';')

  const label = document.createElement('span')
  label.textContent = c.username
  label.style.cssText = [
    'position:absolute',
    'top:-22px',
    'left:-1px',
    `background:${c.color}`,
    'color:#fff',
    'font-size:11px',
    'font-weight:500',
    'font-family:Inter,system-ui,sans-serif',
    'padding:1px 5px',
    'border-radius:4px',
    'white-space:nowrap',
    'pointer-events:none',
    'z-index:50',
    'user-select:none',
  ].join(';')

  wrap.appendChild(caret)
  wrap.appendChild(label)
  return wrap
}

export const RemoteCursors = Extension.create({
  name: 'remoteCursors',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key,
        state: {
          init(): CursorMap { return new Map() },
          apply(tr, cursors): CursorMap {
            const meta = tr.getMeta(key) as { type: string; cursor?: RemoteCursor; id?: number | string } | undefined
            if (!meta) return cursors
            const next = new Map(cursors)
            if (meta.type === 'set' && meta.cursor) {
              next.set(meta.cursor.user_id ?? meta.cursor.username, meta.cursor)
            } else if (meta.type === 'remove' && meta.id !== undefined) {
              next.delete(meta.id)
            } else if (meta.type === 'clear') {
              next.clear()
            }
            return next
          },
        },
        props: {
          decorations(state) {
            const cursors: CursorMap = key.getState(state) ?? new Map()
            const decos: Decoration[] = []
            const maxPos = state.doc.content.size

            for (const [, c] of cursors) {
              const from = Math.max(0, Math.min(c.from, maxPos))
              const to = Math.max(0, Math.min(c.to, maxPos))

              if (from !== to) {
                decos.push(
                  Decoration.inline(Math.min(from, to), Math.max(from, to), {
                    style: `background:${c.color}28;`,
                    class: 'remote-selection',
                  }),
                )
              }

              const caretPos = Math.min(from, Math.max(0, maxPos - 1))
              if (maxPos > 0) {
                decos.push(
                  Decoration.widget(caretPos, () => buildCursorEl(c), {
                    side: -1,
                    key: `rc-${c.user_id ?? c.username}`,
                  }),
                )
              }
            }

            return DecorationSet.create(state.doc, decos)
          },
        },
      }),
    ]
  },
})

export function setCursor(editor: Editor, cursor: RemoteCursor) {
  const { tr } = editor.state
  editor.view.dispatch(tr.setMeta(key, { type: 'set', cursor }))
}

export function removeCursor(editor: Editor, userId: number | null | string) {
  const { tr } = editor.state
  editor.view.dispatch(tr.setMeta(key, { type: 'remove', id: userId }))
}
