<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <EditorToolbar v-if="editor && editable" :editor="editor" :doc-id="docId" :doc-title="docTitle" @docx-imported="emit('docxImported')" />
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-4xl mx-auto px-8 py-10 min-h-full">
        <EditorContent :editor="editor" class="tiptap-editor focus:outline-none min-h-[60vh]" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { Extension } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import EditorToolbar from './EditorToolbar.vue'
import { RemoteCursors, setCursor, removeCursor } from './RemoteCursors'
import type { RemoteCursor } from './RemoteCursors'
import { CommentHighlights, setCommentMarks, getCommentMarks } from './CommentHighlights'
import type { CommentMark } from './CommentHighlights'
import { FontSize } from './FontSize'
import { FontFamily } from './FontFamily'
import apiClient from '../../api/client'
import { resolveMediaUrl } from '../../utils/media'

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
  docId?: number
  docTitle?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number, text: string]
  commentPositionsChanged: [payload: { updated: Array<{ id: number; from: number; to: number; quote: string }>; deleted: number[] }]
  docxImported: []
}>()

let isRemoteUpdate = false
let storedCommentMarks: CommentMark[] = []
let lastEmittedJson = ''
let lastReportedMarksJson = ''

// ── Tab-indent extension for list items ─────────────────────────────────────
const ListIndent = Extension.create({
  name: 'listIndent',
  addKeyboardShortcuts() {
    return {
      Tab: () => {
        if (this.editor.isActive('listItem')) {
          return this.editor.commands.sinkListItem('listItem')
        }
        return false
      },
      'Shift-Tab': () => {
        if (this.editor.isActive('listItem')) {
          return this.editor.commands.liftListItem('listItem')
        }
        return false
      },
    }
  },
})

const editor = useEditor({
  editable: props.editable ?? true,
  extensions: [
    StarterKit,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Image.configure({ inline: false, allowBase64: true }),
    Link.configure({ openOnClick: false }),
    Placeholder.configure({ placeholder: 'Start writing your document…' }),
    TextStyle,
    Color,
    FontSize,
    FontFamily,
    RemoteCursors,
    CommentHighlights,
    ListIndent,
  ],
  content: normalizeContent(props.modelValue),

  editorProps: {
    handlePaste(_view, event) {
      if (!props.docId) return false
      const items = Array.from(event.clipboardData?.items ?? [])
      const imageItem = items.find(item => item.type.startsWith('image/'))
      if (!imageItem) return false
      const file = imageItem.getAsFile()
      if (!file) return false
      event.preventDefault()
      uploadAndInsertImage(file)
      return true
    },
    handleDrop(_view, event, _slice, moved) {
      if (!props.docId || moved) return false
      const files = Array.from((event as DragEvent).dataTransfer?.files ?? [])
      const imageFile = files.find(f => f.type.startsWith('image/'))
      if (!imageFile) return false
      event.preventDefault()
      uploadAndInsertImage(imageFile)
      return true
    },
  },

  onUpdate: ({ editor }) => {
    if (isRemoteUpdate) return
    const json = editor.getJSON()
    lastEmittedJson = JSON.stringify(json)
    emit('update:modelValue', json)
  },
  onSelectionUpdate: ({ editor }) => {
    const { from, to } = editor.state.selection
    const text = from !== to ? editor.state.doc.textBetween(from, to, ' ') : ''
    emit('selectionUpdate', from, to, text)
  },
  onTransaction: ({ editor, transaction }) => {
    if (isRemoteUpdate) return
    if (!transaction.docChanged) return

    const currentMarks = getCommentMarks(editor)
    const currentJson = JSON.stringify(currentMarks)
    if (currentJson === lastReportedMarksJson) return

    const prevById = new Map(storedCommentMarks.map(m => [m.id, m]))
    const currById = new Map(currentMarks.map(m => [m.id, m]))

    const deleted: number[] = []
    for (const id of prevById.keys()) {
      if (!currById.has(id)) deleted.push(id)
    }

    const updated: Array<{ id: number; from: number; to: number; quote: string }> = []
    const docSize = editor.state.doc.content.size
    for (const mark of currentMarks) {
      const prev = prevById.get(mark.id)
      if (!prev || prev.from !== mark.from || prev.to !== mark.to) {
        const safeFrom = Math.max(0, Math.min(mark.from, docSize))
        const safeTo   = Math.max(0, Math.min(mark.to,   docSize))
        const quote = safeFrom < safeTo
          ? editor.state.doc.textBetween(safeFrom, safeTo, ' ')
          : ''
        updated.push({ id: mark.id, from: mark.from, to: mark.to, quote })
      }
    }

    storedCommentMarks = currentMarks
    lastReportedMarksJson = currentJson

    if (updated.length > 0 || deleted.length > 0) {
      emit('commentPositionsChanged', { updated, deleted })
    }
  },
})

// ── image upload ─────────────────────────────────────────────────────────────

async function uploadAndInsertImage(file: File) {
  if (!props.docId || !editor.value) return
  try {
    const formData = new FormData()
    formData.append('image', file)
    const { data } = await apiClient.post<{ url: string }>(
      `/api/docs/${props.docId}/images/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    const src = resolveMediaUrl(data.url) ?? data.url
    editor.value.chain().focus().setImage({ src }).run()
  } catch (e) {
    console.error('Image upload failed', e)
  }
}

// ── helpers ───────────────────────────────────────────────────────────────────

function normalizeContent(val: unknown) {
  if (!val || (typeof val === 'string' && val.trim() === '')) return ''
  if (typeof val === 'string') {
    try { return JSON.parse(val) } catch { return val }
  }
  return val
}

function applyRemote(content: unknown) {
  if (!editor.value) return
  isRemoteUpdate = true

  const { from, to } = editor.value.state.selection
  editor.value.commands.setContent(normalizeContent(content) as string, false)

  const newSize = editor.value.state.doc.content.size
  editor.value.commands.setTextSelection({
    from: Math.min(from, newSize),
    to: Math.min(to, newSize),
  })

  if (storedCommentMarks.length) {
    setCommentMarks(editor.value, storedCommentMarks)
  }

  isRemoteUpdate = false
}

function updateCursor(cursor: RemoteCursor) {
  if (editor.value) setCursor(editor.value, cursor)
}

function clearCursor(userId: number | null | string) {
  if (editor.value) removeCursor(editor.value, userId)
}

function setComments(marks: CommentMark[]) {
  storedCommentMarks = marks
  lastReportedMarksJson = JSON.stringify(marks)
  if (editor.value) setCommentMarks(editor.value, marks)
}

function jumpTo(from: number, to: number) {
  if (!editor.value) return
  editor.value.commands.setTextSelection({ from, to })
  editor.value.commands.scrollIntoView()
}

// ── watchers ──────────────────────────────────────────────────────────────────

watch(
  () => props.modelValue,
  (val) => {
    const incoming = JSON.stringify(normalizeContent(val))
    if (incoming === lastEmittedJson) return
    applyRemote(val)
  },
)

watch(
  () => props.editable,
  (val) => { editor.value?.setEditable(val ?? true) },
)

defineExpose({ applyRemote, updateCursor, clearCursor, setComments, jumpTo })

onBeforeUnmount(() => editor.value?.destroy())
</script>
