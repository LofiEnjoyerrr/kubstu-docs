import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import type { EditorState, Transaction } from '@tiptap/pm/state'

export interface SearchResult {
  from: number
  to: number
}

interface FindReplaceState {
  query: string
  caseSensitive: boolean
  results: SearchResult[]
  active: number
  decorations: DecorationSet
}

export const findReplaceKey = new PluginKey<FindReplaceState>('findReplace')

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    findReplace: {
      setSearch: (query: string, caseSensitive?: boolean) => ReturnType
      clearSearch: () => ReturnType
      gotoNextMatch: () => ReturnType
      gotoPrevMatch: () => ReturnType
      replaceCurrent: (replaceWith: string) => ReturnType
      replaceAll: (replaceWith: string) => ReturnType
    }
  }
}

function computeResults(doc: any, query: string, caseSensitive: boolean): SearchResult[] {
  if (!query) return []
  const results: SearchResult[] = []
  const flags = caseSensitive ? 'g' : 'gi'
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(escaped, flags)

  doc.descendants((node: any, pos: number) => {
    if (!node.isText) return
    const text = node.text ?? ''
    regex.lastIndex = 0
    let m
    while ((m = regex.exec(text)) !== null) {
      results.push({ from: pos + m.index, to: pos + m.index + m[0].length })
      if (m[0].length === 0) regex.lastIndex++
    }
  })

  return results
}

export const FindReplace = Extension.create({
  name: 'findReplace',

  addProseMirrorPlugins() {
    return [
      new Plugin<FindReplaceState>({
        key: findReplaceKey,

        state: {
          init: () => ({
            query: '',
            caseSensitive: false,
            results: [],
            active: -1,
            decorations: DecorationSet.empty,
          }),

          apply(tr: Transaction, prev: FindReplaceState, _oldState, newState) {
            const meta = tr.getMeta(findReplaceKey) as Partial<FindReplaceState> | undefined

            let next = prev
            if (meta) {
              next = { ...prev, ...meta }
            }

            // If the doc changed or query/caseSensitive changed, recompute.
            const needsRecompute =
              tr.docChanged ||
              (meta && ('query' in meta || 'caseSensitive' in meta))

            if (needsRecompute) {
              const results = computeResults(newState.doc, next.query, next.caseSensitive)
              const active = results.length === 0
                ? -1
                : Math.min(Math.max(next.active, 0), results.length - 1)
              next = { ...next, results, active }
            }

            const decos = next.results.map((r, i) =>
              Decoration.inline(r.from, r.to, {
                class: i === next.active ? 'find-match find-match-active' : 'find-match',
              }),
            )
            next = { ...next, decorations: DecorationSet.create(newState.doc, decos) }
            return next
          },
        },

        props: {
          decorations(state: EditorState) {
            return this.getState(state)?.decorations ?? null
          },
        },
      }),
    ]
  },

  addCommands() {
    return {
      setSearch:
        (query: string, caseSensitive = false) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            tr.setMeta(findReplaceKey, { query, caseSensitive, active: 0 })
            dispatch(tr)
          }
          return true
        },

      clearSearch:
        () =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            tr.setMeta(findReplaceKey, {
              query: '',
              results: [],
              active: -1,
              decorations: DecorationSet.empty,
            })
            dispatch(tr)
          }
          return true
        },

      gotoNextMatch:
        () =>
        ({ state, tr, dispatch }) => {
          const s = findReplaceKey.getState(state)
          if (!s || s.results.length === 0) return false
          const next = (s.active + 1) % s.results.length
          if (dispatch) {
            tr.setMeta(findReplaceKey, { active: next })
            const r = s.results[next]
            tr.setSelection((state.selection.constructor as any).create(state.doc, r.from, r.to))
            tr.scrollIntoView()
            dispatch(tr)
          }
          return true
        },

      gotoPrevMatch:
        () =>
        ({ state, tr, dispatch }) => {
          const s = findReplaceKey.getState(state)
          if (!s || s.results.length === 0) return false
          const next = (s.active - 1 + s.results.length) % s.results.length
          if (dispatch) {
            tr.setMeta(findReplaceKey, { active: next })
            const r = s.results[next]
            tr.setSelection((state.selection.constructor as any).create(state.doc, r.from, r.to))
            tr.scrollIntoView()
            dispatch(tr)
          }
          return true
        },

      replaceCurrent:
        (replaceWith: string) =>
        ({ state, tr, dispatch }) => {
          const s = findReplaceKey.getState(state)
          if (!s || s.results.length === 0 || s.active < 0) return false
          const r = s.results[s.active]
          if (dispatch) {
            tr.insertText(replaceWith, r.from, r.to)
            dispatch(tr)
          }
          return true
        },

      replaceAll:
        (replaceWith: string) =>
        ({ state, tr, dispatch }) => {
          const s = findReplaceKey.getState(state)
          if (!s || s.results.length === 0) return false
          if (dispatch) {
            // Replace from right to left so positions stay valid.
            for (let i = s.results.length - 1; i >= 0; i--) {
              const r = s.results[i]
              tr.insertText(replaceWith, r.from, r.to)
            }
            dispatch(tr)
          }
          return true
        },
    }
  },
})

export type { FindReplaceState }
