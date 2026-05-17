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
import { CommentHighlights, setCommentMarks } from './CommentHighlights'
import type { CommentMark } from './CommentHighlights'

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number, text: string]
}>()

let isRemoteUpdate = false

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
    emit('update:modelValue', editor.getJSON())
  },
  onSelectionUpdate: ({ editor }) => {
    const { from, to } = editor.state.selection
    const text = from !== to ? editor.state.doc.textBetween(from, to, ' ') : ''
    emit('selectionUpdate', from, to, text)
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

  // Restore the local cursor after the full-document replace
  const newSize = editor.value.state.doc.content.size
  editor.value.commands.setTextSelection({
    from: Math.min(from, newSize),
    to: Math.min(to, newSize),
  })

  isRemoteUpdate = false
}

function updateCursor(cursor: RemoteCursor) {
  if (editor.value) setCursor(editor.value, cursor)
}

function clearCursor(userId: number | null | string) {
  if (editor.value) removeCursor(editor.value, userId)
}

function setComments(marks: CommentMark[]) {
  if (editor.value) setCommentMarks(editor.value, marks)
}

function jumpTo(from: number, to: number) {
  if (!editor.value) return
  editor.value.commands.setTextSelection({ from, to })
  editor.value.commands.scrollIntoView()
}

watch(
  () => props.modelValue,
  (val) => { applyRemote(val) },
)

watch(
  () => props.editable,
  (val) => { editor.value?.setEditable(val ?? true) },
)

defineExpose({ applyRemote, updateCursor, clearCursor, setComments, jumpTo })

onBeforeUnmount(() => editor.value?.destroy())
</script>
