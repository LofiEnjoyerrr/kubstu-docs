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
  type IRunOptions,
  type ParagraphChild,
} from 'docx'
import { saveAs } from 'file-saver'

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

// ─── helpers ──────────────────────────────────────────────────────────────────

function pxToHalfPts(px: string): number | undefined {
  const n = parseFloat(px)
  if (isNaN(n)) return undefined
  return Math.round(n * 0.75 * 2)
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

function lineSpacing(node: TiptapNode): { line?: number; lineRule?: 'auto' } | undefined {
  const lh = node.attrs?.lineHeight as string | undefined
  if (!lh) return undefined
  const n = parseFloat(lh)
  if (isNaN(n)) return undefined
  // docx wants line in twentieths of a point. For a unitless multiplier we use 240 * n.
  return { line: Math.round(240 * n), lineRule: 'auto' }
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
      const resp = await fetch(src, { credentials: 'include' })
      if (!resp.ok) {
        imageCache.set(src, null)
        return null
      }
      mime = resp.headers.get('content-type') ?? mime
      arrayBuffer = await resp.arrayBuffer()
    }

    // Probe natural size via an <img> so the export keeps proportions.
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

/**
 * Walk the Tiptap JSON, collect every image src, kick off all loads in
 * parallel, and return the cache pre-warmed.
 */
async function preloadImages(node: TiptapNode): Promise<void> {
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

  // Constrain to a sensible printable width (~6 in @ 96 dpi = 576px).
  const MAX_W = 576
  let w = blob.width
  let h = blob.height
  if (w > MAX_W) {
    const scale = MAX_W / w
    w = MAX_W
    h = Math.round(blob.height * scale)
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
    highlight: marks.highlight ? 'yellow' : undefined,
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
    }
  }
  return out
}

// ─── block / paragraph builders ───────────────────────────────────────────────

type Block = Paragraph | Table

function paragraphFromInline(node: TiptapNode): Paragraph {
  return new Paragraph({
    children: inlineContent(node.content),
    alignment: paragraphAlign(node),
    spacing: lineSpacing(node),
  })
}

function convertNode(node: TiptapNode, listDepth = 0): Block[] {
  switch (node.type) {
    case 'doc':
      return (node.content ?? []).flatMap(n => convertNode(n))

    case 'paragraph':
      // A bare image gets its own paragraph so it doesn't collide with text.
      if (node.content && node.content.length === 1 && node.content[0].type === 'image') {
        const run = imageRunForNode(node.content[0])
        if (run) {
          return [new Paragraph({ children: [run], alignment: paragraphAlign(node) })]
        }
      }
      return [paragraphFromInline(node)]

    case 'heading': {
      const level = (node.attrs?.level as number) ?? 1
      return [
        new Paragraph({
          heading: HEADING_MAP[level] ?? HeadingLevel.HEADING_1,
          children: inlineContent(node.content),
          alignment: paragraphAlign(node),
          spacing: lineSpacing(node),
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
                  spacing: lineSpacing(child),
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
                spacing: lineSpacing(child),
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
                  spacing: lineSpacing(child),
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
                indent: { left: 720 },
                alignment: paragraphAlign(child),
                spacing: lineSpacing(child),
              }),
            ]
          : convertNode(child),
      )

    case 'codeBlock': {
      // Re-extract plain text and rebuild runs with a monospace font.
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
      return [new Paragraph({ children: [new PageBreak()] })]

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

// ─── public API ──────────────────────────────────────────────────────────────

export async function exportToDocx(json: unknown, title: string): Promise<void> {
  const root = json as TiptapNode

  // Load every image referenced in the doc before we start building runs.
  await preloadImages(root)

  const children = convertNode(root)

  const doc = new Document({
    creator: 'KubSTU Docs',
    title,
    sections: [{ children: children as any }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `${title || 'document'}.docx`)
}
