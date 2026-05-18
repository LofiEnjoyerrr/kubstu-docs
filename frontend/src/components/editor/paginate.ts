/**
 * Walk a Tiptap JSON doc and compute:
 *   - how many "logical pages" the document defines (one + count of pageBreaks)
 *   - what page number to render in the header/footer at each page
 *
 * The numbering rules match Word:
 *   - Start at ``startAt`` (passed in from the document settings).
 *   - Every time we hit a ``pageBreak`` whose ``restartNumbering`` is true,
 *     reset to ``numberStart`` (or 1 if unspecified) on the *next* page.
 */

export interface PaginationInfo {
  /** ``pageNumbers[i]`` = number to show on page ``i`` (0-based). */
  pageNumbers: number[]
  /** Total number of pages. Always ≥ 1. */
  pageCount: number
}

type TiptapNode = {
  type: string
  attrs?: Record<string, unknown>
  content?: TiptapNode[]
}

export function paginate(doc: TiptapNode | null | undefined, startAt = 1): PaginationInfo {
  const pageNumbers: number[] = []
  let current = Math.max(1, startAt | 0)

  // First page always exists.
  pageNumbers.push(current)

  if (doc && Array.isArray(doc.content)) {
    for (const node of doc.content) {
      if (node.type !== 'pageBreak') continue

      const reset = !!node.attrs?.restartNumbering
      const startOverride = node.attrs?.numberStart
      if (reset) {
        const n =
          typeof startOverride === 'number' && startOverride >= 1
            ? Math.floor(startOverride)
            : 1
        current = n
      } else {
        current += 1
      }
      pageNumbers.push(current)
    }
  }

  return { pageNumbers, pageCount: pageNumbers.length }
}
