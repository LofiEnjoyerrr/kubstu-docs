<template>
  <div class="flex flex-col flex-1 overflow-hidden">
    <EditorToolbar v-if="editor" :editor="editor" />
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

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number]
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
  ],
  content: normalizeContent(props.modelValue),
  onUpdate: ({ editor }) => {
    if (isRemoteUpdate) return
    emit('update:modelValue', editor.getJSON())
  },
  onSelectionUpdate: ({ editor }) => {
    const { from, to } = editor.state.selection
    emit('selectionUpdate', from, to)
  },
})

function normalizeContent(val: unknown) {
  if (!val || (typeof val === 'string' && val.trim() === '')) return ''
  if (typeof val === 'string') {
    try { return JSON.parse(val) } catch { return val }
  }
  return val
}

// Apply remote content without triggering our own onUpdate
function applyRemote(content: unknown) {
  if (!editor.value) return
  isRemoteUpdate = true
  editor.value.commands.setContent(normalizeContent(content) as string, false)
  isRemoteUpdate = false
}

watch(
  () => props.modelValue,
  (val) => { applyRemote(val) },
)

watch(
  () => props.editable,
  (val) => { editor.value?.setEditable(val ?? true) },
)

defineExpose({ applyRemote })

onBeforeUnmount(() => editor.value?.destroy())
</script>
