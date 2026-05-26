import Image from '@tiptap/extension-image'
import { mergeAttributes } from '@tiptap/core'
import { resolveMediaUrl } from '../../utils/media'

function toPositiveNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) && value > 0 ? value : null
  if (typeof value !== 'string') return null
  const n = parseFloat(value)
  return Number.isFinite(n) && n > 0 ? n : null
}

function sizeStyle(style: unknown, width: number | null, height: number | null): string | undefined {
  const parts = typeof style === 'string' && style.trim() ? [style.trim().replace(/;$/, '')] : []
  if (width !== null) parts.push(`width: ${Math.round(width)}px`)
  if (height !== null) parts.push(`height: ${Math.round(height)}px`)
  return parts.length ? `${parts.join('; ')};` : undefined
}

/**
 * Drop-in replacement for Tiptap's Image that resolves relative media URLs and
 * keeps image size attributes in the document JSON so resized images survive
 * save, collaboration sync, and DOCX export.
 */
export const ResolvedImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: null,
        parseHTML: element =>
          toPositiveNumber(element.getAttribute('width')) ??
          toPositiveNumber((element as HTMLElement).style.width),
        renderHTML: attributes => {
          const width = toPositiveNumber(attributes.width)
          return width === null ? {} : { width: Math.round(width) }
        },
      },
      height: {
        default: null,
        parseHTML: element =>
          toPositiveNumber(element.getAttribute('height')) ??
          toPositiveNumber((element as HTMLElement).style.height),
        renderHTML: attributes => {
          const height = toPositiveNumber(attributes.height)
          return height === null ? {} : { height: Math.round(height) }
        },
      },
      floating: {
        default: null,
        renderHTML: () => ({}),
      },
    }
  },

  renderHTML({ HTMLAttributes }) {
    const attrs = { ...HTMLAttributes }
    const src = attrs.src
    if (typeof src === 'string') {
      attrs.src = resolveMediaUrl(src) ?? src
    }

    const width = toPositiveNumber(attrs.width)
    const height = toPositiveNumber(attrs.height)
    attrs.style = sizeStyle(attrs.style, width, height)

    return [
      'img',
      mergeAttributes(this.options.HTMLAttributes, attrs),
    ]
  },

  addNodeView() {
    return ({ node, editor, getPos }) => {
      let currentNode = node
      let resizing = false
      let startX = 0
      let startWidth = 0
      let startHeight = 0
      let draftWidth = 0
      let draftHeight = 0

      const dom = document.createElement('span')
      dom.className = 'resizable-image-node'
      dom.contentEditable = 'false'

      const img = document.createElement('img')
      const handle = document.createElement('span')
      handle.className = 'resizable-image-handle'
      handle.title = 'Изменить размер изображения'

      dom.append(img, handle)

      const applyNodeAttrs = () => {
        const attrs = currentNode.attrs
        img.src = resolveMediaUrl(attrs.src) ?? attrs.src
        img.alt = attrs.alt ?? ''
        img.title = attrs.title ?? ''

        const width = toPositiveNumber(attrs.width)
        const height = toPositiveNumber(attrs.height)
        img.style.width = width === null ? '' : `${Math.round(width)}px`
        img.style.height = height === null ? '' : `${Math.round(height)}px`
      }

      const updateImageAttrs = (width: number, height: number) => {
        if (typeof getPos !== 'function') return
        const pos = getPos()
        if (typeof pos !== 'number') return
        editor.view.dispatch(
          editor.state.tr.setNodeMarkup(pos, undefined, {
            ...currentNode.attrs,
            width: Math.round(width),
            height: Math.round(height),
          }),
        )
      }

      const stopResize = () => {
        if (!resizing) return
        resizing = false
        dom.classList.remove('is-resizing')
        document.removeEventListener('mousemove', onResizeMove)
        document.removeEventListener('mouseup', stopResize)
        updateImageAttrs(draftWidth, draftHeight)
      }

      const onResizeMove = (event: MouseEvent) => {
        if (!resizing) return
        event.preventDefault()
        const dx = event.clientX - startX
        const aspect = startHeight > 0 ? startWidth / startHeight : 1
        const editorWidth = (dom.closest('.ProseMirror') as HTMLElement | null)?.clientWidth ?? editor.view.dom.clientWidth
        const maxWidth = Math.max(40, editorWidth || startWidth)
        draftWidth = Math.min(maxWidth, Math.max(40, startWidth + dx))
        draftHeight = Math.max(40, draftWidth / aspect)
        img.style.width = `${Math.round(draftWidth)}px`
        img.style.height = `${Math.round(draftHeight)}px`
      }

      handle.addEventListener('mousedown', (event) => {
        if (!editor.isEditable) return
        event.preventDefault()
        event.stopPropagation()

        const rect = img.getBoundingClientRect()
        startX = event.clientX
        startWidth = toPositiveNumber(currentNode.attrs.width) ?? rect.width ?? img.naturalWidth ?? 120
        startHeight = toPositiveNumber(currentNode.attrs.height) ?? rect.height ?? img.naturalHeight ?? 90
        draftWidth = startWidth
        draftHeight = startHeight
        resizing = true
        dom.classList.add('is-resizing')
        document.addEventListener('mousemove', onResizeMove)
        document.addEventListener('mouseup', stopResize)
      })

      applyNodeAttrs()

      return {
        dom,
        update: (updatedNode) => {
          if (updatedNode.type !== currentNode.type) return false
          currentNode = updatedNode
          if (!resizing) applyNodeAttrs()
          return true
        },
        selectNode: () => dom.classList.add('ProseMirror-selectednode'),
        deselectNode: () => dom.classList.remove('ProseMirror-selectednode'),
        stopEvent: event => resizing || event.target === handle,
        destroy: () => {
          document.removeEventListener('mousemove', onResizeMove)
          document.removeEventListener('mouseup', stopResize)
        },
      }
    }
  },
})
