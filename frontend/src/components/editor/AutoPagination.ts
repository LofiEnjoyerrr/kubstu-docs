import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import type { EditorView } from '@tiptap/pm/view'
import type { EditorState } from '@tiptap/pm/state'

/**
 * Inserts visual page-break decorations whenever the document overflows
 * the configured page height — the same way Microsoft Word and Google
 * Docs flow text across pages as you type.
 *
 * Two cases to handle:
 *   1. Block-level overflow — a new paragraph wouldn't fit on the page.
 *      Easy: split before that block.
 *   2. Intra-block overflow — a single paragraph (or image) is taller
 *      than a page on its own. We probe the editor's coordinate space
 *      with ``view.posAtCoords`` at every page boundary to find the doc
 *      position where the new page should start, then drop a widget
 *      decoration there. The widget renders inline-block, breaking the
 *      visual flow.
 *
 * Auto breaks live in plugin state, not in the doc, so:
 *   - they never get serialized into the saved JSON or DOCX
 *   - they recompute every time you type / resize / change layout
 *   - they don't pollute undo history or the collaborative broadcast
 */

interface AutoPaginationState {
  /** Doc positions where a visual break should appear (between blocks
   *  OR inside one, e.g. mid-paragraph). */
  positions: number[]
  /** Page height in CSS pixels EXCLUDING top + bottom margins. */
  pageHeight: number
}

export const autoPaginationKey = new PluginKey<AutoPaginationState>('autoPagination')

export interface AutoPaginationOptions {
  pageHeight: number
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    autoPagination: {
      /** Update the available content height per page. */
      setAutoPageHeight: (px: number) => ReturnType
    }
  }
}

/**
 * Visual height consumed by a single auto-break widget.
 *
 * Breaks render as a clearly visible "between-pages" gap so the user can
 * tell where one page ends and the next begins. The gap takes real layout
 * space, so the plugin advances ``currentPageTop`` by this many pixels
 * past each break it inserts — that's how the next page's first line ends
 * up at the right Y coordinate.
 *
 * KEEP IN SYNC with the ``height`` of ``.tiptap-editor .page-break`` in
 * TiptapEditor.vue. Editor and DOCX still match text-per-page because the
 * exporter strips break widgets and re-injects them as hard page breaks
 * at the same doc positions — Word never sees the visual gap.
 */
const BREAK_VISUAL_HEIGHT = 40

/**
 * Find the doc position at viewport Y `targetY` within a block node.
 *
 * `posAtCoords` uses `document.elementFromPoint` which returns null for
 * coordinates outside the visible viewport — so it silently fails for any
 * page break that falls below the scroll fold. When that happens we fall
 * back to a binary search over `coordsAtPos`, which measures actual DOM
 * rects and works for any position regardless of scroll.
 */
function posAtViewportY(
  view: EditorView,
  targetY: number,
  probeX: number,
  nodeStart: number,
  nodeSize: number,
): number | null {
  const screenH = window.innerHeight || document.documentElement.clientHeight

  // Fast path: target is inside the visible viewport.
  if (targetY >= 0 && targetY <= screenH) {
    const hit = view.posAtCoords({ left: probeX, top: targetY })
    return hit?.pos ?? null
  }

  // Off-screen: binary-search using coordsAtPos, which works for any doc
  // position even when the element is outside the viewport.
  const lo0 = nodeStart + 1
  const hi0 = nodeStart + nodeSize - 1
  if (lo0 >= hi0) return null

  // Find the smallest position where coordsAtPos(pos).top >= targetY.
  let lo = lo0
  let hi = hi0
  for (let iter = 0; iter < 40; iter++) {
    const mid = (lo + hi) >> 1
    if (mid <= lo) break
    let top: number
    try {
      top = view.coordsAtPos(mid).top
    } catch {
      break
    }
    if (top < targetY) lo = mid
    else hi = mid
  }

  if (hi <= lo0 || hi >= hi0) return null
  return hi
}

function buildBreakEl(): HTMLElement {
  const wrap = document.createElement('div')
  wrap.className = 'page-break auto-page-break'
  wrap.setAttribute('data-auto-page-break', 'true')
  wrap.setAttribute('contenteditable', 'false')

  // Empty span updated by updatePageBreakChrome when page numbers are on.
  const label = document.createElement('span')
  label.className = 'page-break-page-label'
  wrap.appendChild(label)

  return wrap
}

function arraysEqual(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false
  return true
}

export const AutoPagination = Extension.create<AutoPaginationOptions>({
  name: 'autoPagination',

  addOptions() {
    return { pageHeight: 864 }
  },

  addCommands() {
    return {
      setAutoPageHeight:
        (px: number) =>
        ({ tr, dispatch }) => {
          if (dispatch) {
            tr.setMeta(autoPaginationKey, { pageHeight: px })
            dispatch(tr)
          }
          return true
        },
    }
  },

  addProseMirrorPlugins() {
    const initialHeight = this.options.pageHeight

    return [
      new Plugin<AutoPaginationState>({
        key: autoPaginationKey,

        state: {
          init: () => ({ positions: [], pageHeight: initialHeight }),
          apply(tr, prev) {
            const meta = tr.getMeta(autoPaginationKey) as Partial<AutoPaginationState> | undefined
            if (!meta) return prev
            return { ...prev, ...meta }
          },
        },

        props: {
          decorations(state) {
            const s = autoPaginationKey.getState(state)
            if (!s || s.positions.length === 0) return null
            const decos = s.positions.map((pos) =>
              Decoration.widget(pos, () => buildBreakEl(), {
                key: `auto-pb-${pos}`,
                side: -1,
                ignoreSelection: true,
              }),
            )
            return DecorationSet.create(state.doc, decos)
          },
        },

        view(view) {
          let scheduled = false
          let destroyed = false

          function recompute() {
            if (destroyed) return
            try {
              recomputeInner()
            } catch (e) {
              // Don't let a measurement error break the editor; just
              // try again on the next view update.
              if (typeof console !== 'undefined') {
                console.warn('[AutoPagination] recompute failed', e)
              }
            }
          }

          function recomputeInner() {
            const state = view.state
            const s = autoPaginationKey.getState(state)
            const pageHeight = s?.pageHeight ?? initialHeight
            if (pageHeight <= 0) return

            const root = view.dom as HTMLElement
            const editorRect = root.getBoundingClientRect()
            // Editor not laid out yet (hidden / mid-mount); retry later.
            if (editorRect.height === 0 || editorRect.width === 0) return

            const allChildren = Array.from(root.children) as HTMLElement[]
            const blockEls = allChildren.filter(
              (c) => !c.hasAttribute('data-auto-page-break'),
            )

            const positions: number[] = []
            // Viewport Y where the current page starts. Advances past each
            // manual break and each auto break we insert.
            let currentPageTop = editorRect.top
            let blockIdx = 0

            state.doc.forEach((node, offset) => {
              const el = blockEls[blockIdx]
              blockIdx += 1
              if (!el) return

              const elRect = el.getBoundingClientRect()

              // Manual page/section breaks end the current page — the
              // next block starts a fresh page right after them.
              if (node.type.name === 'pageBreak' || node.type.name === 'sectionBreak') {
                currentPageTop = elRect.bottom
                return
              }

              if (elRect.height === 0) return

              const blockTop = elRect.top
              const blockBottom = elRect.bottom
              const pageBottomY = currentPageTop + pageHeight

              // Whole block fits on the current page?
              if (blockBottom <= pageBottomY + 0.5) {
                return
              }

              // Block overflows. If there's content on the current page
              // ABOVE the block, push a break before the block so it
              // starts on a fresh page.
              if (blockTop > currentPageTop + 0.5) {
                positions.push(offset)
                currentPageTop = blockTop
              }

              // If the block, on its own, is still taller than a page,
              // we need to break INSIDE the block. We probe the editor
              // at every page-bottom Y and let ProseMirror tell us what
              // doc position corresponds to that pixel.
              let pageBottomNow = currentPageTop + pageHeight
              const probeX = elRect.left + Math.max(40, elRect.width * 0.5)
              let safety = 0
              while (blockBottom > pageBottomNow + 0.5 && safety < 200) {
                safety++
                const pos = posAtViewportY(view, pageBottomNow, probeX, offset, node.nodeSize)
                if (pos === null) break

                // The position must sit AFTER this block's start, AFTER
                // any previously pushed break, and BEFORE the block's
                // end. If any of those fail, bail out — the algorithm
                // can resume on the next recompute once the decorations
                // we're about to insert have settled into the layout.
                if (pos <= offset) break
                if (positions.length > 0 && pos <= positions[positions.length - 1]) break
                if (pos >= offset + node.nodeSize) break

                positions.push(pos)
                // The next page starts past this break. We add the break
                // widget's height so the next probe falls in real content
                // rather than landing inside the break we just placed.
                currentPageTop = pageBottomNow + BREAK_VISUAL_HEIGHT
                pageBottomNow = currentPageTop + pageHeight
              }
            })

            dispatchIfChanged(positions)
          }

          function dispatchIfChanged(newPositions: number[]) {
            if (destroyed) return
            const current = autoPaginationKey.getState(view.state)?.positions ?? []
            if (arraysEqual(newPositions, current)) return
            view.dispatch(view.state.tr.setMeta(autoPaginationKey, { positions: newPositions }))
          }

          function schedule() {
            if (scheduled || destroyed) return
            scheduled = true
            requestAnimationFrame(() => {
              scheduled = false
              recompute()
            })
          }

          // Listen for window resizes — block widths can change without
          // a transaction, and that changes wrapping which changes
          // heights which changes where pages break.
          const onResize = () => schedule()
          window.addEventListener('resize', onResize)

          // Initial pass after the editor's first paint. Doing it twice
          // in quick succession buys the layout enough time to settle
          // before we measure (StarterKit's placeholder, font loading,
          // etc. can shift heights between the first and second frame).
          schedule()
          setTimeout(schedule, 50)

          return {
            update: schedule,
            destroy: () => {
              destroyed = true
              window.removeEventListener('resize', onResize)
            },
          }
        },
      }),
    ]
  },
})

/** Read the current automatic break positions from the editor's state. */
export function getAutoBreakPositions(state: EditorState): number[] {
  return autoPaginationKey.getState(state)?.positions ?? []
}
