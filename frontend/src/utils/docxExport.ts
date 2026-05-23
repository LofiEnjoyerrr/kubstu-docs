import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  UnderlineType,
  ImageRun,
  ExternalHyperlink,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  ShadingType,
  PageBreak,
  Header,
  Footer,
  PageNumber as DocxPageNumber,
  NumberFormat,
  PageOrientation,
  type IRunOptions,
  type ParagraphChild,
} from 'docx'
import { saveAs } from 'file-saver'
import { resolveMediaUrl } from './media'
import {
  DEFAULT_FONT_FAMILY,
  DEFAULT_FONT_SIZE_HALF_POINTS,
  DEFAULT_LINE_SPACING_TWIPS,
} from '../components/editor/typographyDefaults'
import type { PageLayout } from '../types'

// ─── types ────────────────────────────────────────────────────────────────────

type TiptapMark = { type: string; attrs?: Record<string, unknown> }

type TiptapNode = {
  type: string
  text?: string
  attrs?: Record<string, unknown>
  marks?: TiptapMark[]
  content?: TiptapNode[]
}

type ImageBlob = { data: ArrayBuffer; mime: string; width: number; height: number }

export interface ExportOptions {
  pageLayout?: PageLayout
  headerJson?: unknown
  footerJson?: unknown
  showPageNumbers?: boolean
  pageNumberStart?: number
}

// ─── mappings ────────────────────────────────────────────────────────────────

const HEADING_MAP: Record<number, (typeof HeadingLevel)[keyof typeof HeadingLevel]> = {
  1: HeadingLevel.HEADING_1,
  2: HeadingLevel.HEADING_2,
  3: HeadingLevel.HEADING_3,
  4: HeadingLevel.HEADING_4,
  5: HeadingLevel.HEADING_5,
  6: HeadingLevel.HEADING_6,
}

const ALIGN_MAP: Record<string, (typeof AlignmentType)[keyof typeof AlignmentType]> = {
  left: AlignmentType.LEFT,
  center: AlignmentType.CENTER,
  right: AlignmentType.RIGHT,
  justify: AlignmentType.JUSTIFIED,
}

// ─── unit helpers ─────────────────────────────────────────────────────────────

const PX_PER_INCH = 96
const TWIPS_PER_INCH = 1440

function pxToTwips(px: number | string | undefined): number | undefined {
  if (px == null) return undefined
  const n = typeof px === 'string' ? parseFloat(px) : px
  if (isNaN(n)) return undefined
  return Math.round((n / PX_PER_INCH) * TWIPS_PER_INCH)
}

/**
 * Convert a CSS font-size string (``"12pt"`` or legacy ``"12px"``) into the
 * half-points Word uses for ``<w:sz w:val="…"/>``. Both units are treated
 * as point sizes so that the number the user picks from the toolbar
 * dropdown exactly matches the size that appears in the exported DOCX.
 * Without this, a "12" in the dropdown was being interpreted as 12 px
 * and exported as 9 pt.
 */
function pxToHalfPts(size: string): number | undefined {
  const m = size.match(/^([\d.]+)/)
  if (!m) return undefined
  const n = parseFloat(m[1])
  if (isNaN(n)) return undefined
  return Math.round(n * 2)
}

function colorToDocxHex(color: string | undefined | null): string | undefined {
  if (!color) return undefined
  const hex6 = color.match(/^#?([0-9a-fA-F]{6})$/)
  if (hex6) return hex6[1].toUpperCase()
  const hex3 = color.match(/^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/)
  if (hex3) {
    return (hex3[1] + hex3[1] + hex3[2] + hex3[2] + hex3[3] + hex3[3]).toUpperCase()
  }
  const rgb = color.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/)
  if (rgb) {
    return [rgb[1], rgb[2], rgb[3]]
      .map(n => parseInt(n, 10).toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase()
  }
  return undefined
}

function paragraphAlign(node: TiptapNode): (typeof AlignmentType)[keyof typeof AlignmentType] | undefined {
  const ta = node.attrs?.textAlign as string | undefined
  return ta ? ALIGN_MAP[ta] : undefined
}

function lineSpacing(node: TiptapNode): { line?: number; lineRule?: 'exact' } | undefined {
  // We only emit a ``<w:spacing>`` for paragraphs whose Tiptap node carries
  // an explicit ``lineHeight`` attribute. The Tiptap attribute is a unitless
  // CSS multiplier (e.g. ``"1.5"``), interpreted against the run's font size.
  // To preserve that intent in Word we convert it to an *exact* twips value
  // — ``lineRule="auto"`` would let Word fall back to natural metrics for
  // single-spaced paragraphs (defeating the purpose). Paragraphs without
  // ``lineHeight`` get no line spec, which lets Word use the font's natural
  // line height — matching the editor's ``line-height: normal`` default.
  const lh = node.attrs?.lineHeight as string | undefined
  if (!lh) return undefined
  const n = parseFloat(lh)
  if (isNaN(n)) return undefined
  const fontSizePt = readRunFontSizePt(node) ?? 14
  const twips = Math.round(n * fontSizePt * 20)
  return { line: twips, lineRule: 'exact' }
}

function readRunFontSizePt(node: TiptapNode): number | undefined {
  // Find the first text run's ``fontSize`` mark to anchor the line-height
  // multiplier against. Without this we'd assume 14pt for every paragraph,
  // so a paragraph whose runs are explicitly 11pt would round-trip with
  // a line that's ~27% too tall.
  for (const child of node.content ?? []) {
    if (child.type !== 'text') continue
    const ts = child.marks?.find(m => m.type === 'textStyle')
    const size = (ts?.attrs as Record<string, string> | undefined)?.fontSize
    if (!size) continue
    const m = size.match(/^([\d.]+)/)
    if (!m) continue
    const n = parseFloat(m[1])
    if (!isNaN(n)) return n
  }
  return undefined
}

function paragraphSpacing(node: TiptapNode): any {
  const a = (node.attrs ?? {}) as Record<string, string>
  const ls = lineSpacing(node)
  const before = pxToTwips(a.marginTop)
  const after = pxToTwips(a.marginBottom)
  if (!ls && before === undefined && after === undefined) return undefined
  return {
    ...(ls ?? {}),
    ...(before !== undefined ? { before } : {}),
    ...(after !== undefined ? { after } : {}),
  }
}

function paragraphIndent(node: TiptapNode): any {
  const a = (node.attrs ?? {}) as Record<string, string>
  const left = pxToTwips(a.marginLeft)
  const right = pxToTwips(a.marginRight)
  const firstLine = pxToTwips(a.textIndent)
  if (left === undefined && right === undefined && firstLine === undefined) return undefined
  const out: any = {}
  if (left !== undefined) out.left = left
  if (right !== undefined) out.right = right
  if (firstLine !== undefined) {
    if (firstLine >= 0) out.firstLine = firstLine
    else out.hanging = -firstLine
  }
  return out
}

// ─── image loading & sizing ───────────────────────────────────────────────────

const imageCache = new Map<string, ImageBlob | null>()

async function loadImage(src: string): Promise<ImageBlob | null> {
  if (imageCache.has(src)) return imageCache.get(src) ?? null
  try {
    let arrayBuffer: ArrayBuffer
    let mime = 'image/png'

    if (src.startsWith('data:')) {
      const m = /^data:([^;]+);base64,(.*)$/.exec(src)
      if (!m) {
        imageCache.set(src, null)
        return null
      }
      mime = m[1]
      const bin = atob(m[2])
      const bytes = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
      arrayBuffer = bytes.buffer
    } else {
      // DOCX-imported images are stored as ``/media/...`` relative paths.
      // In dev that resolves to ``http://localhost:5173`` (Vite) which has
      // nothing to serve. ``resolveMediaUrl`` prepends the API base so the
      // fetch hits Django regardless of which dev port the page is on.
      const fetchUrl = resolveMediaUrl(src) ?? src
      const resp = await fetch(fetchUrl, { credentials: 'include' })
      if (!resp.ok) {
        imageCache.set(src, null)
        return null
      }
      mime = resp.headers.get('content-type') ?? mime
      arrayBuffer = await resp.arrayBuffer()
    }

    const { width, height } = await probeImageSize(arrayBuffer, mime)
    const blob: ImageBlob = { data: arrayBuffer, mime, width, height }
    imageCache.set(src, blob)
    return blob
  } catch (e) {
    console.warn('Image export load failed', src, e)
    imageCache.set(src, null)
    return null
  }
}

function probeImageSize(buffer: ArrayBuffer, mime: string): Promise<{ width: number; height: number }> {
  return new Promise(resolve => {
    const blob = new Blob([buffer], { type: mime })
    const url = URL.createObjectURL(blob)
    const img = new window.Image()
    img.onload = () => {
      const w = img.naturalWidth || 600
      const h = img.naturalHeight || 400
      URL.revokeObjectURL(url)
      resolve({ width: w, height: h })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve({ width: 600, height: 400 })
    }
    img.src = url
  })
}

async function preloadImages(node: TiptapNode | null): Promise<void> {
  if (!node) return
  const sources = new Set<string>()
  collectSources(node, sources)
  await Promise.all([...sources].map(s => loadImage(s)))
}

function collectSources(node: TiptapNode, out: Set<string>): void {
  if (node.type === 'image' && typeof node.attrs?.src === 'string') {
    out.add(node.attrs.src as string)
  }
  if (node.content) node.content.forEach(c => collectSources(c, out))
}

function imageRunForNode(node: TiptapNode): ImageRun | null {
  const src = node.attrs?.src as string | undefined
  if (!src) return null
  const blob = imageCache.get(src)
  if (!blob) return null

  const explicitW = node.attrs?.width as number | undefined
  const explicitH = node.attrs?.height as number | undefined

  const MAX_W = 576
  let w = explicitW ?? blob.width
  let h = explicitH ?? blob.height
  if (w > MAX_W) {
    const scale = MAX_W / w
    w = MAX_W
    h = Math.round((explicitH ?? blob.height) * scale)
  }

  return new ImageRun({
    data: blob.data as any,
    type: (blob.mime.split('/')[1] || 'png') as any,
    transformation: { width: w, height: h },
  })
}

// ─── inline builders ──────────────────────────────────────────────────────────

function buildTextRun(node: TiptapNode, parentMarks: TiptapMark[] = []): ParagraphChild {
  const marks = Object.fromEntries(
    [...(parentMarks ?? []), ...(node.marks ?? [])].map(m => [m.type, m]),
  )
  const tsAttrs = (marks.textStyle?.attrs ?? {}) as Record<string, string>

  const baseRun: IRunOptions = {
    text: node.text ?? '',
    bold: !!marks.bold,
    italics: !!marks.italic,
    underline: marks.underline ? { type: UnderlineType.SINGLE } : undefined,
    strike: !!marks.strike,
    size: tsAttrs.fontSize ? pxToHalfPts(tsAttrs.fontSize) : undefined,
    font: tsAttrs.fontFamily || undefined,
    color: colorToDocxHex(tsAttrs.color),
    superScript: !!marks.superscript,
    subScript: !!marks.subscript,
    shading: marks.highlight?.attrs?.color
      ? {
          type: ShadingType.SOLID,
          color: colorToDocxHex(marks.highlight.attrs.color as string) || 'FFFF00',
          fill: colorToDocxHex(marks.highlight.attrs.color as string) || 'FFFF00',
        }
      : undefined,
  }

  if (marks.link) {
    const href = (marks.link.attrs?.href as string) ?? ''
    return new ExternalHyperlink({
      link: href,
      children: [
        new TextRun({
          ...baseRun,
          color: baseRun.color ?? '0563C1',
          underline: { type: UnderlineType.SINGLE },
        }),
      ],
    })
  }

  return new TextRun(baseRun)
}

function inlineContent(content: TiptapNode[] = [], parentMarks: TiptapMark[] = []): ParagraphChild[] {
  const out: ParagraphChild[] = []
  for (const n of content) {
    if (n.type === 'text') {
      out.push(buildTextRun(n, parentMarks))
    } else if (n.type === 'hardBreak') {
      out.push(new TextRun({ text: '', break: 1 }))
    } else if (n.type === 'image') {
      const r = imageRunForNode(n)
      if (r) out.push(r)
    } else if (n.type === 'pageNumber') {
      // Word "PAGE" or "NUMPAGES" field.
      const kind = (n.attrs?.kind as string) ?? 'number'
      const which = kind === 'count' ? DocxPageNumber.TOTAL_PAGES : DocxPageNumber.CURRENT
      out.push(new TextRun({ children: [which] }))
    }
  }
  return out
}

// ─── block / paragraph builders ───────────────────────────────────────────────

type Block = Paragraph | Table

function convertNode(node: TiptapNode, listDepth = 0): Block[] {
  switch (node.type) {
    case 'doc':
      return (node.content ?? []).flatMap(n => convertNode(n))

    case 'paragraph':
      if (node.content && node.content.length === 1 && node.content[0].type === 'image') {
        const run = imageRunForNode(node.content[0])
        if (run) {
          return [
            new Paragraph({
              children: [run],
              alignment: paragraphAlign(node),
              spacing: paragraphSpacing(node),
              indent: paragraphIndent(node),
            }),
          ]
        }
      }
      return [
        new Paragraph({
          children: inlineContent(node.content),
          alignment: paragraphAlign(node),
          spacing: paragraphSpacing(node),
          indent: paragraphIndent(node),
        }),
      ]

    case 'heading': {
      const level = (node.attrs?.level as number) ?? 1
      return [
        new Paragraph({
          heading: HEADING_MAP[level] ?? HeadingLevel.HEADING_1,
          children: inlineContent(node.content),
          alignment: paragraphAlign(node),
          spacing: paragraphSpacing(node),
          indent: paragraphIndent(node),
        }),
      ]
    }

    case 'bulletList':
      return (node.content ?? []).flatMap(item =>
        (item.content ?? []).flatMap(child =>
          child.type === 'paragraph'
            ? [
                new Paragraph({
                  children: inlineContent(child.content),
                  bullet: { level: listDepth },
                  alignment: paragraphAlign(child),
                  spacing: paragraphSpacing(child),
                }),
              ]
            : convertNode(child, listDepth + 1),
        ),
      )

    case 'orderedList': {
      let counter = (node.attrs?.start as number) ?? 1
      return (node.content ?? []).flatMap(item =>
        (item.content ?? []).flatMap(child => {
          if (child.type === 'paragraph') {
            const num = counter++
            return [
              new Paragraph({
                children: [
                  new TextRun({ text: `${num}. ` }),
                  ...inlineContent(child.content),
                ],
                alignment: paragraphAlign(child),
                spacing: paragraphSpacing(child),
              }),
            ]
          }
          return convertNode(child, listDepth + 1)
        }),
      )
    }

    case 'taskList':
      return (node.content ?? []).flatMap(item => {
        const checked = !!item.attrs?.checked
        return (item.content ?? []).flatMap(child =>
          child.type === 'paragraph'
            ? [
                new Paragraph({
                  children: [
                    new TextRun({ text: checked ? '☒ ' : '☐ ' }),
                    ...inlineContent(child.content),
                  ],
                  spacing: paragraphSpacing(child),
                }),
              ]
            : convertNode(child),
        )
      })

    case 'blockquote':
      return (node.content ?? []).flatMap(child =>
        child.type === 'paragraph'
          ? [
              new Paragraph({
                children: [
                  new TextRun({ text: '❝ ', italics: true }),
                  ...inlineContent(child.content),
                ],
                indent: { left: 720, ...paragraphIndent(child) },
                alignment: paragraphAlign(child),
                spacing: paragraphSpacing(child),
              }),
            ]
          : convertNode(child),
      )

    case 'codeBlock': {
      const codeRuns: ParagraphChild[] = (node.content ?? []).map(child => {
        if (child.type === 'text') {
          return new TextRun({ text: child.text ?? '', font: 'Courier New' })
        }
        return new TextRun({ text: '', break: 1 })
      })
      return [
        new Paragraph({
          children: codeRuns,
          shading: { type: ShadingType.SOLID, color: 'F1F5F9', fill: 'F1F5F9' },
        }),
      ]
    }

    case 'horizontalRule':
      return [
        new Paragraph({
          border: {
            bottom: { color: '999999', space: 1, style: BorderStyle.SINGLE, size: 6 },
          },
        }),
      ]

    case 'image': {
      const run = imageRunForNode(node)
      return run ? [new Paragraph({ children: [run] })] : []
    }

    case 'table':
      return [buildTable(node)]

    case 'hardBreak':
      return [new Paragraph({ children: [new TextRun({ text: '', break: 1 })] })]

    case 'pageBreak':
      // A page break that doesn't restart numbering is just an inline
      // ``<w:br w:type="page"/>``. Breaks that DO restart numbering are
      // promoted to Word section breaks by ``splitIntoSections`` upstream
      // — they never reach this switch.
      return [new Paragraph({ children: [new PageBreak()] })]

    case 'sectionBreak':
      // Section breaks are handled at the document level (one Word section
      // per group). They produce no inline output here.
      return []

    default:
      return []
  }
}

function buildTable(node: TiptapNode): Table {
  const rows = (node.content ?? []).map(row => {
    const cells = (row.content ?? []).map(cell => {
      const isHeader = cell.type === 'tableHeader'
      return new TableCell({
        children: (cell.content ?? []).flatMap(child => convertNode(child)) as any,
        shading: isHeader
          ? { type: ShadingType.SOLID, color: 'F1F5F9', fill: 'F1F5F9' }
          : undefined,
        columnSpan: (cell.attrs?.colspan as number) || undefined,
        rowSpan: (cell.attrs?.rowspan as number) || undefined,
      })
    })
    return new TableRow({ children: cells })
  })

  return new Table({
    rows,
    width: { size: 100, type: WidthType.PERCENTAGE },
  })
}

// ─── header / footer builders ────────────────────────────────────────────────

function buildBandChildren(json: unknown): Paragraph[] {
  if (!json || typeof json !== 'object') {
    return [new Paragraph({ children: [] })]
  }
  const blocks = convertNode(json as TiptapNode)
  // Word headers/footers want at least one paragraph.
  return blocks.length > 0
    ? (blocks.filter(b => b instanceof Paragraph) as Paragraph[])
    : [new Paragraph({ children: [] })]
}

// ─── section grouping ────────────────────────────────────────────────────────

interface SectionGroup {
  children: TiptapNode[]
  /** What page number this section's first page should display. */
  pageNumberStart: number
  /** When true, this section continues the previous section's numbering. */
  continueNumbering: boolean
}

/**
 * Splits the body's top-level children into Word sections. Each ``sectionBreak``
 * node (and every ``pageBreak`` flagged ``restartNumbering``) starts a new
 * section. The break node itself is consumed — its semantics live on the
 * resulting section's properties.
 */
function splitIntoSections(root: TiptapNode, initialStart: number): SectionGroup[] {
  const sections: SectionGroup[] = []
  let current: TiptapNode[] = []
  let currentStart = Math.max(1, initialStart | 0)
  let currentContinue = false

  for (const node of root.content ?? []) {
    if (node.type === 'sectionBreak') {
      sections.push({ children: current, pageNumberStart: currentStart, continueNumbering: currentContinue })
      current = []
      const reset = node.attrs?.restartNumbering !== false
      if (reset) {
        currentStart = ((node.attrs?.numberStart as number) ?? 1) | 0
        currentContinue = false
      } else {
        currentContinue = true
      }
    } else if (node.type === 'pageBreak' && node.attrs?.restartNumbering) {
      // A page break that restarts numbering becomes a section break in Word.
      sections.push({ children: current, pageNumberStart: currentStart, continueNumbering: currentContinue })
      current = []
      currentStart = ((node.attrs?.numberStart as number) ?? 1) | 0
      currentContinue = false
    } else {
      current.push(node)
    }
  }

  sections.push({ children: current, pageNumberStart: currentStart, continueNumbering: currentContinue })
  return sections
}

// ─── public API ──────────────────────────────────────────────────────────────

export async function exportToDocx(
  json: unknown,
  title: string,
  options: ExportOptions = {},
): Promise<void> {
  // We deliberately do NOT bake the editor's auto-pagination positions into
  // the DOCX. Doing that turned each invisible seam into a real
  // ``<w:br w:type="page"/>``, and re-importing the file would surface those
  // breaks as labeled manual page breaks the user never asked for. The
  // editor and Word share page size + font defaults (see typographyDefaults
  // and the docDefaults below), so Word paginates the document on its own
  // at the same boundaries the editor showed.
  const root = json as TiptapNode

  // Pre-load every image referenced in the body, header, and footer.
  await Promise.all([
    preloadImages(root),
    preloadImages(options.headerJson as TiptapNode | undefined as TiptapNode | null),
    preloadImages(options.footerJson as TiptapNode | undefined as TiptapNode | null),
  ])

  // Compose a Header / Footer if the user defined one OR if page numbers
  // are enabled (numbering needs SOME footer to live in). Each Word section
  // gets a fresh Header/Footer instance (the docx library does not let you
  // reuse the same one across sections).
  const headerHasContent = bandHasContent(options.headerJson)
  const footerHasContent = bandHasContent(options.footerJson)
  const wantsPageNumbers = !!options.showPageNumbers

  function makeHeader() {
    return headerHasContent
      ? { default: new Header({ children: buildBandChildren(options.headerJson) }) }
      : undefined
  }

  function makeFooter() {
    let footerChildren: Paragraph[] = []
    if (footerHasContent) {
      footerChildren = buildBandChildren(options.footerJson)
    } else if (wantsPageNumbers) {
      footerChildren = [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [DocxPageNumber.CURRENT] })],
        }),
      ]
    }
    return footerChildren.length > 0
      ? { default: new Footer({ children: footerChildren }) }
      : undefined
  }

  const layout = options.pageLayout
  function basePageProps() {
    if (!layout) return undefined
    return {
      size: {
        width: pxToTwips(layout.page_width),
        height: pxToTwips(layout.page_height),
        orientation: layout.page_width > layout.page_height
          ? PageOrientation.LANDSCAPE
          : PageOrientation.PORTRAIT,
      },
      margin: {
        top: pxToTwips(layout.margin_top),
        right: pxToTwips(layout.margin_right),
        bottom: pxToTwips(layout.margin_bottom),
        left: pxToTwips(layout.margin_left),
      },
    }
  }

  const groups = splitIntoSections(root, options.pageNumberStart ?? 1)

  const sections = groups.map((group) => {
    const groupRoot: TiptapNode = { type: 'doc', content: group.children }
    const groupChildren = convertNode(groupRoot)
    // Word requires every section to contain at least one paragraph.
    if (groupChildren.length === 0) {
      groupChildren.push(new Paragraph({ children: [] }))
    }
    const page: any = basePageProps() ?? {}
    if (!group.continueNumbering) {
      page.pageNumbers = {
        start: group.pageNumberStart,
        formatType: NumberFormat.DECIMAL,
      }
    }
    return {
      properties: { page },
      headers: makeHeader(),
      footers: makeFooter(),
      children: groupChildren as any,
    }
  })

  const doc = new Document({
    creator: 'KubSTU Docs',
    title,
    // Document defaults — runs/paragraphs without explicit values pick these
    // up so the DOCX renders text at the same density as the editor.
    //
    // ``before: 0, after: 0`` matters: Word's built-in Normal style adds 8pt
    // after each paragraph, which would let Word fit noticeably fewer lines
    // per page than the editor (the editor's CSS reset puts zero margin on
    // <p>). Setting these here aligns the two.
    //
    // Pin docDefaults line spacing to the same fixed multiplier the editor
    // uses via CSS ``line-height: 1.2`` (DEFAULT_LINE_SPACING_TWIPS in
    // typographyDefaults). ``lineRule="atLeast"`` so taller inline content
    // (e.g. an image in a paragraph) gets the room it needs without being
    // clipped, while text-only paragraphs land on exactly the same pixel
    // height in both renderers.
    styles: {
      default: {
        document: {
          run: {
            font: DEFAULT_FONT_FAMILY,
            size: DEFAULT_FONT_SIZE_HALF_POINTS,
          },
          paragraph: {
            spacing: {
              before: 0,
              after: 0,
              line: DEFAULT_LINE_SPACING_TWIPS,
              lineRule: 'atLeast',
            },
          },
        },
      },
    },
    sections,
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `${title || 'document'}.docx`)
}

function bandHasContent(json: unknown): boolean {
  if (!json || typeof json !== 'object') return false
  const root = json as TiptapNode
  if (!root.content?.length) return false
  return root.content.some((n) =>
    n.type !== 'paragraph' || (n.content && n.content.length > 0),
  )
}
