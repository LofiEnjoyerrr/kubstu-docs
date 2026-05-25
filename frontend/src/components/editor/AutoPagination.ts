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
 * Visual height consumed by a single auto-break widget — kept as a
 * documentation anchor for the CSS coupling. The current measurement
 * algorithm hides the widgets before measuring (see ``recomputeInner``),
 * so this number doesn't appear in any arithmetic; it just records what
 * the CSS reserves for the gap between pages.
 *
 * KEEP IN SYNC with the ``height`` of ``.tiptap-editor .page-break`` in
 * TiptapEditor.vue. Editor and DOCX still match text-per-page because the
 * exporter strips break widgets and re-injects them as hard page breaks
 * at the same doc positions — Word never sees the visual gap.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const BREAK_VISUAL_HEIGHT = 40

/**
 * Find the doc position at viewport Y `targetY` within a block node.
 *
 * `posAtCoords` uses `document.elementFromPoint` which returns null for
 * coordinates outside the visible viewport — so it silently fails for any
 * page break that falls below the scroll fold. When that happens we fall
 * back to a binary search over `coordsAtPos`, which measures actual DOM
 * rects and works for any position regardless of scroll.
 *
 * The returned position is ALWAYS snapped to the start of its visual line.
 * Without this snap the break widget can land mid-word: ``posAtCoords``
 * is happy to return a position between two characters of the same word
 * (sub-pixel rounding plus the way browsers expose the leftmost text rect
 * on justified lines), and a ``display: block`` widget inserted there
 * forces the browser to render half the word on the current page and the
 * other half on the next. Snapping back to the line start guarantees the
 * widget always sits between two visual lines, so the whole straddling
 * line moves to the next page as a unit.
 */
function posAtViewportY(
  view: EditorView,
  targetY: number,
  probeX: number,
  nodeStart: number,
  nodeSize: number,
): number | null {
  const screenH = window.innerHeight || document.documentElement.clientHeight

  let candidate: number | null = null

  // Fast path: target is inside the visible viewport.
  if (targetY >= 0 && targetY <= screenH) {
    const hit = view.posAtCoords({ left: probeX, top: targetY })
    candidate = hit?.pos ?? null
  }

  if (candidate === null) {
    // Off-screen (or posAtCoords couldn't resolve): binary-search using
    // coordsAtPos, which works for any doc position even when the
    // element is outside the viewport.
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
    candidate = hi
  }

  return snapToLineStart(view, candidate, nodeStart)
}

/**
 * Walk backwards from ``pos`` to the smallest position within the same
 * block whose ``coordsAtPos(...).top`` matches the input position's top —
 * i.e. the first character of the visual line containing ``pos``. This
 * keeps the auto-pagination widget from ever landing inside a word.
 *
 * Then ensure the result is a real word boundary in the underlying text.
 * The line-start snap alone has a feedback loop: when the widget is
 * already at a mid-word position (which can happen during fast typing
 * before the recompute catches up, or right after the user extends the
 * last word on a page so it overflows), the visual line *after* that
 * widget starts mid-word, and a fresh snap to its start lands on the
 * exact same bad position. The widget never moves and the user sees a
 * word split across the page boundary indefinitely. Walking backwards
 * from the line start to the next whitespace breaks the loop — the
 * widget snaps to the start of the wrapping word, the word stays
 * intact on one page, and the layout settles.
 */
function snapToLineStart(view: EditorView, pos: number, nodeStart: number): number {
  let targetTop: number
  try {
    targetTop = view.coordsAtPos(pos).top
  } catch {
    return pos
  }

  // Tolerate sub-pixel rounding when comparing line tops — Chrome
  // occasionally reports the same visual line as ``250.4`` for one
  // character and ``250.6`` for the next.
  const EPSILON = 1.5

  let lo = nodeStart + 1
  let hi = pos
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    let top: number
    try {
      top = view.coordsAtPos(mid).top
    } catch {
      lo = mid + 1
      continue
    }
    if (top < targetTop - EPSILON) lo = mid + 1
    else hi = mid
  }

  return snapToWordBoundary(view, lo, nodeStart)
}

/**
 * Walk backwards from ``pos`` until we land immediately after whitespace
 * (or hit the start of the block). Capped at ``MAX_LOOKBACK`` characters
 * so that a single very long unbreakable token can't make us scan the
 * whole doc — in that pathological case we just return ``pos`` and let
 * the break land wherever it does.
 */
function snapToWordBoundary(view: EditorView, pos: number, nodeStart: number): number {
  const MAX_LOOKBACK = 256
  const doc = view.state.doc
  const floor = Math.max(nodeStart + 1, pos - MAX_LOOKBACK)

  let p = pos
  while (p > floor) {
    let ch: string
    try {
      ch = doc.textBetween(p - 1, p, '\n', '\n')
    } catch {
      break
    }
    // ``ch`` is empty when ``p - 1`` sits on a node boundary (e.g. a
    // hardBreak or the start of an inline node). Treat that as a word
    // boundary too — anything before it is necessarily a separate
    // "word" in the layout sense.
    if (!ch || /\s/.test(ch)) return p
    p--
  }
  return pos
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

            // Hide every currently-rendered auto-break widget BEFORE we
            // measure. This is the heart of the algorithm: without it,
            // each widget inflates the bottom of the block it lives in
            // (both by its own ``BREAK_VISUAL_HEIGHT`` and — more
            // importantly — by forcing the wrapping word onto a fresh
            // line below the widget). Subtracting only the widget height
            // (the old ``widgetsContribution`` heuristic) under-corrected
            // by exactly one line, so once a word wrapped to page 2 the
            // measured bottom stayed above the page boundary even after
            // the user deleted the characters that caused the wrap — and
            // the widget never went away.
            //
            // Hiding the widgets gives us the true "as if no auto-breaks
            // existed" layout, so ``elRect.bottom`` is the natural
            // bottom and the comparison against ``pageBottomNow`` is
            // exact. Browsers compute style changes synchronously when
            // a measurement is taken right after, so the swap happens
            // without a paint in between — no flicker.
            const widgetEls = Array.from(
              root.querySelectorAll<HTMLElement>('.auto-page-break'),
            )
            const savedDisplay = widgetEls.map((w) => w.style.display)
            widgetEls.forEach((w) => {
              w.style.display = 'none'
            })

            try {
              // Re-read editor rect AFTER hiding widgets: with the
              // widgets removed from the flow, the editor's height
              // shrinks, but its TOP is unchanged. We still use the
              // original top as the page-1 origin — that's stable.
              const allChildren = Array.from(root.children) as HTMLElement[]
              const blockEls = allChildren.filter(
                (c) => !c.hasAttribute('data-auto-page-break'),
              )

              const positions: number[] = []
              // Viewport Y where the current page starts. Advances past
              // each manual break and each auto break we insert. With
              // widgets hidden, this stays aligned with the natural
              // layout's logical "page N top".
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

                let pageBottomNow = currentPageTop + pageHeight

                // Whole block fits on the current page in the natural
                // (no-widget) layout? Then we don't need a break.
                if (elRect.bottom <= pageBottomNow + 0.5) {
                  return
                }

                // Block overflows the current page. Probe for an
                // intra-block break first — that's what Word does by
                // default and what the user expects: fill the current
                // page with as many of the block's lines as fit, then
                // wrap the rest onto the next page.
                //
                // Probe at the LEFT edge of the block, not the middle.
                // ``posAtCoords({left: middleX, top: pageBottomY})``
                // would return a doc position in the middle of whichever
                // line straddles ``pageBottomY`` — inserting a block
                // widget there forces a visual line break mid-word.
                // Probing at the left edge instead returns the START of
                // the straddling line, so the whole line moves to the
                // next page and the previous line fills out to the
                // right margin like Word and Google Docs do.
                const probeX = elRect.left + 1
                let safety = 0
                let pushedAny = false
                while (elRect.bottom > pageBottomNow + 0.5 && safety < 200) {
                  safety++
                  const pos = posAtViewportY(view, pageBottomNow, probeX, offset, node.nodeSize)
                  if (pos === null) break

                  if (pos <= offset) {
                    // The probe landed at or before the block's first
                    // position — there's no line of THIS block we can
                    // keep on the current page. That happens for
                    // atomic blocks (images, manual breaks) and for
                    // paragraphs whose first line already starts below
                    // the page boundary. Fall back to a "page break
                    // before block" ONLY on the first iteration — once
                    // we have already pushed an intra-break we mustn't
                    // push another one at the same place.
                    if (!pushedAny && elRect.top > currentPageTop + 0.5) {
                      positions.push(offset)
                      pushedAny = true
                      currentPageTop = elRect.top
                      pageBottomNow = currentPageTop + pageHeight
                      continue
                    }
                    break
                  }

                  // The position must sit AFTER any previously pushed
                  // break and BEFORE the block's end.
                  if (positions.length > 0 && pos <= positions[positions.length - 1]) break
                  if (pos >= offset + node.nodeSize) break

                  positions.push(pos)
                  pushedAny = true
                  currentPageTop = pageBottomNow
                  pageBottomNow = currentPageTop + pageHeight
                }
              })

              dispatchIfChanged(positions)
            } finally {
              // Restore widget display. If ``dispatchIfChanged`` removed
              // the widgets via a state update, the DOM nodes in
              // ``widgetEls`` may now be detached — assigning to .style
              // on a detached element is harmless.
              widgetEls.forEach((w, i) => {
                w.style.display = savedDisplay[i]
              })
            }
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
