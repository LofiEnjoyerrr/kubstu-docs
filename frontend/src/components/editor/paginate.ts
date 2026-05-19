/**
 * Walk a Tiptap JSON doc and compute the layout of logical pages — how many
 * there are, which page number each shows in its header/footer, and which
 * "section" each page belongs to.
 *
 * The numbering rules match Word / Google Docs:
 *   - Start at ``startAt`` (passed in from the document settings).
 *   - Every time we hit a ``pageBreak`` whose ``restartNumbering`` is true,
 *     reset to ``numberStart`` (or 1 if unspecified) on the next page.
 *   - A ``sectionBreak`` always starts a new page AND opens a new section.
 *     Section breaks may also restart numbering (default: yes, at 1).
 */

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

type TiptapNode = {
  type: string
  attrs?: Record<string, unknown>
  content?: TiptapNode[]
}

export function paginate(doc: TiptapNode | null | undefined, startAt = 1): PaginationInfo {
  const pageNumbers: number[] = []
  const sectionIds: number[] = []
  let current = Math.max(1, startAt | 0)
  let section = 0

  // First page always exists.
  pageNumbers.push(current)
  sectionIds.push(section)

  if (doc && Array.isArray(doc.content)) {
    for (const node of doc.content) {
      if (node.type === 'pageBreak') {
        const reset = !!node.attrs?.restartNumbering
        const startOverride = node.attrs?.numberStart
        if (reset) {
          current =
            typeof startOverride === 'number' && startOverride >= 1
              ? Math.floor(startOverride)
              : 1
        } else {
          current += 1
        }
        pageNumbers.push(current)
        sectionIds.push(section)
      } else if (node.type === 'sectionBreak') {
        section += 1
        const reset = node.attrs?.restartNumbering !== false
        const startOverride = node.attrs?.numberStart
        if (reset) {
          current =
            typeof startOverride === 'number' && startOverride >= 1
              ? Math.floor(startOverride)
              : 1
        } else {
          current += 1
        }
        pageNumbers.push(current)
        sectionIds.push(section)
      }
    }
  }

  return {
    pageNumbers,
    sectionIds,
    pageCount: pageNumbers.length,
    sectionCount: section + 1,
  }
}
