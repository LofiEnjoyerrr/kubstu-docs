<template>
  <div class="flex flex-col flex-1 overflow-hidden bg-slate-100">
    <EditorToolbar
      v-if="editor && editable"
      :editor="editor"
      :doc-id="docId"
      :doc-title="docTitle"
      :page-layout="pageLayout"
      @docx-imported="payload => emit('docxImported', payload)"
      @update-page-layout="layout => emit('updatePageLayout', layout)"
    />
    <div class="flex-1 overflow-y-auto">
      <div
        class="mx-auto my-8 bg-white shadow-lg transition-[width,padding] duration-150"
        :style="pageStyle"
      >
        <EditorContent :editor="editor" class="tiptap-editor focus:outline-none min-h-[60vh]" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, computed, onBeforeUnmount } from 'vue'
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
import Highlight from '@tiptap/extension-highlight'
import Subscript from '@tiptap/extension-subscript'
import Superscript from '@tiptap/extension-superscript'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import EditorToolbar from './EditorToolbar.vue'
import { RemoteCursors, setCursor, removeCursor } from './RemoteCursors'
import type { RemoteCursor } from './RemoteCursors'
import { CommentHighlights, setCommentMarks, getCommentMarks } from './CommentHighlights'
import type { CommentMark } from './CommentHighlights'
import { FontSize } from './FontSize'
import { FontFamily } from './FontFamily'
import { LineHeight } from './LineHeight'
import { FindReplace } from './FindReplace'
import apiClient from '../../api/client'
import { resolveMediaUrl } from '../../utils/media'
import type { PageLayout } from '../../types'

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
  docId?: number
  docTitle?: string
  pageLayout: PageLayout
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number, text: string]
  commentPositionsChanged: [payload: { updated: Array<{ id: number; from: number; to: number; quote: string }>; deleted: number[] }]
  docxImported: [payload: { content: unknown }]
  updatePageLayout: [layout: Partial<PageLayout>]
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
        if (this.editor.isActive('taskItem')) {
          return this.editor.commands.sinkListItem('taskItem')
        }
        if (this.editor.isActive('listItem')) {
          return this.editor.commands.sinkListItem('listItem')
        }
        return false
      },
      'Shift-Tab': () => {
        if (this.editor.isActive('taskItem')) {
          return this.editor.commands.liftListItem('taskItem')
        }
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
    Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
    Placeholder.configure({ placeholder: 'Start writing your document…' }),
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
    Subscript,
    Superscript,
    Table.configure({ resizable: true, allowTableNodeSelection: true }),
    TableRow,
    TableHeader,
    TableCell,
    TaskList,
    TaskItem.configure({ nested: true }),
    FontSize,
    FontFamily,
    LineHeight,
    FindReplace,
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

// ── page layout styling ─────────────────────────────────────────────────────

const pageStyle = computed(() => {
  const l = props.pageLayout
  return {
    width: `${l.page_width}px`,
    paddingTop: `${l.margin_top}px`,
    paddingRight: `${l.margin_right}px`,
    paddingBottom: `${l.margin_bottom}px`,
    paddingLeft: `${l.margin_left}px`,
    minHeight: `${Math.round(l.page_width * 1.414)}px`, // ~A4 aspect
    boxSizing: 'border-box' as const,
  }
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

<style>
/* Find & replace highlights — global so they can target ProseMirror's
   decoration spans which sit outside the scoped style boundary. */
.find-match {
  background: rgba(250, 204, 21, 0.45);
  border-radius: 2px;
}
.find-match-active {
  background: rgba(249, 115, 22, 0.65);
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.5);
}

/* Tables */
.tiptap-editor table {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;
  margin: 1rem 0;
  overflow: hidden;
}
.tiptap-editor table td,
.tiptap-editor table th {
  border: 1px solid #cbd5e1;
  padding: 6px 10px;
  vertical-align: top;
  position: relative;
  min-width: 1em;
}
.tiptap-editor table th {
  background: #f1f5f9;
  font-weight: 600;
  text-align: left;
}
.tiptap-editor table .selectedCell::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(37, 99, 235, 0.15);
  pointer-events: none;
}
.tiptap-editor .tableWrapper {
  overflow-x: auto;
}
.tiptap-editor table .column-resize-handle {
  position: absolute;
  right: -2px;
  top: 0;
  bottom: -2px;
  width: 4px;
  background-color: #3b82f6;
  pointer-events: none;
}

/* Task list */
.tiptap-editor ul[data-type='taskList'] {
  list-style: none;
  padding: 0;
}
.tiptap-editor ul[data-type='taskList'] li {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}
.tiptap-editor ul[data-type='taskList'] li > label {
  margin-top: 0.25rem;
  user-select: none;
}
.tiptap-editor ul[data-type='taskList'] li > div {
  flex: 1;
}

/* Highlight */
.tiptap-editor mark {
  padding: 0 2px;
  border-radius: 2px;
}
</style>
