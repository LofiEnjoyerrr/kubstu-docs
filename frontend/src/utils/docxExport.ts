import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  UnderlineType,
} from 'docx'
import { saveAs } from 'file-saver'

// ─── helpers ────────────────────────────────────────────────────────────────

type TiptapNode = {
  type: string
  text?: string
  attrs?: Record<string, unknown>
  marks?: Array<{ type: string; attrs?: Record<string, unknown> }>
  content?: TiptapNode[]
}

const HEADING_MAP: Record<number, (typeof HeadingLevel)[keyof typeof HeadingLevel]> = {
  1: HeadingLevel.HEADING_1,
  2: HeadingLevel.HEADING_2,
  3: HeadingLevel.HEADING_3,
}

const ALIGN_MAP: Record<string, (typeof AlignmentType)[keyof typeof AlignmentType]> = {
  left: AlignmentType.LEFT,
  center: AlignmentType.CENTER,
  right: AlignmentType.RIGHT,
  justify: AlignmentType.JUSTIFIED,
}

/** px string → half-points (docx size unit). Approximation: 1px ≈ 0.75pt, 1pt = 2 half-pts */
function pxToHalfPts(px: string): number | undefined {
  const n = parseFloat(px)
  if (isNaN(n)) return undefined
  return Math.round(n * 0.75 * 2)
}

/**
 * Normalise any CSS colour string to the 6-digit uppercase hex that the
 * `docx` library requires (no leading #).
 * Handles: #rrggbb · #rgb · rrggbb · rgb(r,g,b) · rgba(r,g,b,a)
 */
function colorToDocxHex(color: string | undefined | null): string | undefined {
  if (!color) return undefined

  // bare 6-digit hex or #rrggbb
  const hex6 = color.match(/^#?([0-9a-fA-F]{6})$/)
  if (hex6) return hex6[1].toUpperCase()

  // #rgb shorthand → expand
  const hex3 = color.match(/^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/)
  if (hex3) {
    return (hex3[1] + hex3[1] + hex3[2] + hex3[2] + hex3[3] + hex3[3]).toUpperCase()
  }

  // rgb(r, g, b) / rgba(r, g, b, a)
  const rgb = color.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/)
  if (rgb) {
    return [rgb[1], rgb[2], rgb[3]]
      .map(n => parseInt(n, 10).toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase()
  }

  return undefined // unknown format — omit the colour
}

function buildTextRun(node: TiptapNode): TextRun {
  const marks = Object.fromEntries((node.marks ?? []).map(m => [m.type, m]))
  const tsAttrs = (marks.textStyle?.attrs ?? {}) as Record<string, string>

  return new TextRun({
    text: node.text ?? '',
    bold: !!marks.bold,
    italics: !!marks.italic,
    underline: marks.underline ? { type: UnderlineType.SINGLE } : undefined,
    strike: !!marks.strike,
    size: tsAttrs.fontSize ? pxToHalfPts(tsAttrs.fontSize) : undefined,
    font: tsAttrs.fontFamily || undefined,
    color: colorToDocxHex(tsAttrs.color),
  })
}

function inlineContent(content: TiptapNode[] = []): TextRun[] {
  const runs: TextRun[] = []
  for (const n of content) {
    if (n.type === 'text') runs.push(buildTextRun(n))
    else if (n.type === 'hardBreak') runs.push(new TextRun({ text: '', break: 1 }))
  }
  return runs
}

function paragraphAlign(node: TiptapNode): (typeof AlignmentType)[keyof typeof AlignmentType] | undefined {
  const ta = node.attrs?.textAlign as string | undefined
  return ta ? ALIGN_MAP[ta] : undefined
}

// ─── node converter ──────────────────────────────────────────────────────────

function convertNode(node: TiptapNode, listDepth = 0): Paragraph[] {
  switch (node.type) {
    case 'doc':
      return (node.content ?? []).flatMap(n => convertNode(n))

    case 'paragraph':
      return [
        new Paragraph({
          children: inlineContent(node.content),
          alignment: paragraphAlign(node),
        }),
      ]

    case 'heading': {
      const level = (node.attrs?.level as number) ?? 1
      return [
        new Paragraph({
          heading: HEADING_MAP[level] ?? HeadingLevel.HEADING_1,
          children: inlineContent(node.content),
        }),
      ]
    }

    case 'bulletList':
      return (node.content ?? []).flatMap((item, _i) =>
        (item.content ?? []).flatMap(child =>
          child.type === 'paragraph'
            ? [
                new Paragraph({
                  children: inlineContent(child.content),
                  bullet: { level: listDepth },
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
              }),
            ]
          }
          return convertNode(child, listDepth + 1)
        }),
      )
    }

    case 'blockquote':
      return (node.content ?? []).flatMap(child =>
        child.type === 'paragraph'
          ? [
              new Paragraph({
                children: [
                  new TextRun({ text: '❝ ' }),
                  ...inlineContent(child.content),
                ],
              }),
            ]
          : convertNode(child),
      )

    case 'codeBlock':
      return [
        new Paragraph({
          children: inlineContent(node.content),
          style: 'IntenseQuote',
        }),
      ]

    case 'horizontalRule':
      return [new Paragraph({ text: '────────────────────────────────────' })]

    default:
      // passthrough for unknown nodes (image, etc.)
      return []
  }
}

// ─── public API ──────────────────────────────────────────────────────────────

export async function exportToDocx(json: unknown, title: string): Promise<void> {
  const children = convertNode(json as TiptapNode)

  const doc = new Document({
    sections: [{ children }],
  })

  const blob = await Packer.toBlob(doc)
  saveAs(blob, `${title || 'document'}.docx`)
}
