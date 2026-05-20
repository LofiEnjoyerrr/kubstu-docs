/**
 * Walk an editor state and compute the layout of logical pages — how many
 * there are, which page number each shows in its header/footer, and which
 * "section" each page belongs to.
 *
 * The numbering rules match Word / Google Docs:
 *   - Start at ``startAt`` (passed in from the document settings).
 *   - Every time we hit a ``pageBreak`` whose ``restartNumbering`` is true,
 *     reset to ``numberStart`` (or 1 if unspecified) on the next page.
 *   - A ``sectionBreak`` always starts a new page AND opens a new section.
 *     Section breaks may also restart numbering (default: yes, at 1).
 *   - Automatic breaks (from the ``AutoPagination`` plugin) simply
 *     increment the page number — they're a layout artefact, not a
 *     numbering directive.
 */

import type { EditorState } from '@tiptap/pm/state'

export interface PaginationInfo {
  /** ``pageNumbers[i]`` = number to show on page ``i`` (0-based). */
  pageNumbers: number[]
  /** ``sectionIds[i]`` = which section page ``i`` belongs to (0-based). */
  sectionIds: number[]
  /** Total number of pages. Always ≥ 1. */
  pageCount: number
  /** Total number of distinct sections. Always ≥ 1. */
  sectionCount: number
}

interface BreakEntry {
  pos: number
  type: 'pageBreak' | 'sectionBreak' | 'auto'
  attrs?: Record<string, unknown>
}

export function paginate(
  state: EditorState,
  startAt = 1,
  autoBreakPositions: number[] = [],
): PaginationInfo {
  const breaks: BreakEntry[] = []

  state.doc.forEach((node, offset) => {
    if (node.type.name === 'pageBreak') {
      breaks.push({ pos: offset, type: 'pageBreak', attrs: node.attrs })
    } else if (node.type.name === 'sectionBreak') {
      breaks.push({ pos: offset, type: 'sectionBreak', attrs: node.attrs })
    }
  })

  for (const pos of autoBreakPositions) {
    breaks.push({ pos, type: 'auto' })
  }

  // Merge in document order. When a manual break sits at the same
  // position as an auto break, the manual one wins so its numbering
  // semantics aren't overridden.
  breaks.sort((a, b) => {
    if (a.pos !== b.pos) return a.pos - b.pos
    if (a.type === 'auto') return 1
    if (b.type === 'auto') return -1
    return 0
  })

  const pageNumbers: number[] = []
  const sectionIds: number[] = []
  let current = Math.max(1, startAt | 0)
  let section = 0

  pageNumbers.push(current)
  sectionIds.push(section)

  for (const br of breaks) {
    if (br.type === 'sectionBreak') {
      section += 1
      const reset = br.attrs?.restartNumbering !== false
      if (reset) {
        const start = br.attrs?.numberStart
        current = typeof start === 'number' && start >= 1 ? Math.floor(start) : 1
      } else {
        current += 1
      }
    } else if (br.type === 'pageBreak') {
      const reset = !!br.attrs?.restartNumbering
      if (reset) {
        const start = br.attrs?.numberStart
        current = typeof start === 'number' && start >= 1 ? Math.floor(start) : 1
      } else {
        current += 1
      }
    } else {
      // auto break — just advance.
      current += 1
    }
    pageNumbers.push(current)
    sectionIds.push(section)
  }

  return {
    pageNumbers,
    sectionIds,
    pageCount: pageNumbers.length,
    sectionCount: section + 1,
  }
}
