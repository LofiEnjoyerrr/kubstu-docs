<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <EditorToolbar v-if="editor && editable" :editor="editor" />
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

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number, text: string]
  commentPositionsChanged: [payload: { updated: Array<{ id: number; from: number; to: number; quote: string }>; deleted: number[] }]
}>()

let isRemoteUpdate = false
let storedCommentMarks: CommentMark[] = []
// Stringified JSON of the last content we emitted ourselves.
// Used to detect the v-model round-trip (parent reflects our own emit back
// as a prop change) and skip calling applyRemote / setContent for it —
// that would otherwise reset comment positions on every keystroke.
let lastEmittedJson = ''
// Stringified JSON of the last comment-marks state we reported outward.
// Used to skip emitting commentPositionsChanged when nothing actually moved.
let lastReportedMarksJson = ''

const editor = useEditor({
  editable: props.editable ?? true,
  extensions: [
    StarterKit,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Image,
    Link.configure({ openOnClick: false }),
    Placeholder.configure({ placeholder: 'Start writing your document…' }),
    TextStyle,
    Color,
    RemoteCursors,
    CommentHighlights,
  ],
  content: normalizeContent(props.modelValue),
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
    // Only react to local document mutations; skip remote updates and
    // non-document transactions (cursor moves, meta-only dispatches, etc.).
    if (isRemoteUpdate) return
    if (!transaction.docChanged) return

    const currentMarks = getCommentMarks(editor)
    const currentJson = JSON.stringify(currentMarks)
    if (currentJson === lastReportedMarksJson) return

    // Build sets for quick lookup
    const prevById = new Map(storedCommentMarks.map(m => [m.id, m]))
    const currById = new Map(currentMarks.map(m => [m.id, m]))

    // Comments whose range collapsed to nothing → delete them
    const deleted: number[] = []
    for (const id of prevById.keys()) {
      if (!currById.has(id)) deleted.push(id)
    }

    // Comments whose boundaries moved → update them
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

  // Restore the local cursor after the full-document replace.
  const newSize = editor.value.state.doc.content.size
  editor.value.commands.setTextSelection({
    from: Math.min(from, newSize),
    to: Math.min(to, newSize),
  })

  // setContent issues a full-replace transaction which collapses all mapped
  // comment positions to 0. Re-apply the canonical server positions so
  // highlights remain visible after remote edits.
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

watch(
  () => props.modelValue,
  (val) => {
    // Skip the round-trip: when the user edits locally, onUpdate emits the new
    // JSON upward, the parent stores it in editorContent, and Vue reflects it
    // back here as a prop change. That would call setContent() and wipe the
    // in-flight comment position mapping. Compare against the last thing we
    // emitted and bail out if they match.
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
