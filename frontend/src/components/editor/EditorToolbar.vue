<template>
  <div class="flex flex-wrap items-center gap-0.5 px-3 py-2 border-b border-slate-200 bg-white">
    <!-- Text style -->
    <div class="flex items-center gap-0.5 pr-2 border-r border-slate-200 mr-1">
      <select
        class="h-7 px-2 rounded text-xs border border-slate-200 text-slate-700 focus:outline-none focus:border-primary-400 bg-white"
        @change="setHeading($event)"
      >
        <option value="0">Paragraph</option>
        <option value="1">Heading 1</option>
        <option value="2">Heading 2</option>
        <option value="3">Heading 3</option>
      </select>
    </div>

    <!-- Formatting -->
    <div class="flex items-center gap-0.5 pr-2 border-r border-slate-200 mr-1">
      <ToolBtn :active="editor.isActive('bold')" title="Bold (Ctrl+B)" @click="editor.chain().focus().toggleBold().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15.6 11.8A4 4 0 0013 5H7v14h6.5a4.5 4.5 0 002.1-8.2zM9 7h4a2 2 0 010 4H9V7zm4.5 10H9v-4h4.5a2.5 2.5 0 010 5z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('italic')" title="Italic (Ctrl+I)" @click="editor.chain().focus().toggleItalic().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4v3h2.21l-3.42 8H6v3h8v-3h-2.21l3.42-8H18V4z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('underline')" title="Underline (Ctrl+U)" @click="editor.chain().focus().toggleUnderline().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 17c3.31 0 6-2.69 6-6V3h-2.5v8c0 1.93-1.57 3.5-3.5 3.5S8.5 12.93 8.5 11V3H6v8c0 3.31 2.69 6 6 6zm-7 2v2h14v-2H5z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('strike')" title="Strikethrough" @click="editor.chain().focus().toggleStrike().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 19h4v-3h-4v3zM5 4v3h5v3h4V7h5V4H5zM3 14h18v-2H3v2z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('code')" title="Inline code" @click="editor.chain().focus().toggleCode().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
      </ToolBtn>
    </div>

    <!-- Alignment -->
    <div class="flex items-center gap-0.5 pr-2 border-r border-slate-200 mr-1">
      <ToolBtn :active="editor.isActive({ textAlign: 'left' })" title="Align left" @click="editor.chain().focus().setTextAlign('left').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15 15H3v2h12v-2zm0-8H3v2h12V7zM3 13h18v-2H3v2zm0 8h18v-2H3v2zM3 3v2h18V3H3z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive({ textAlign: 'center' })" title="Center" @click="editor.chain().focus().setTextAlign('center').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M7 15v2h10v-2H7zm-4 6h18v-2H3v2zm0-8h18v-2H3v2zm4-6v2h10V7H7zM3 3v2h18V3H3z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive({ textAlign: 'right' })" title="Align right" @click="editor.chain().focus().setTextAlign('right').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zm6-4h12v-2H9v2zm-6-4h18v-2H3v2zm6-4h12V7H9v2zM3 3v2h18V3H3z"/></svg>
      </ToolBtn>
    </div>

    <!-- Lists -->
    <div class="flex items-center gap-0.5 pr-2 border-r border-slate-200 mr-1">
      <ToolBtn :active="editor.isActive('bulletList')" title="Bullet list" @click="editor.chain().focus().toggleBulletList().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('orderedList')" title="Numbered list" @click="editor.chain().focus().toggleOrderedList().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M2 17h2v.5H3v1h1v.5H2v1h3v-4H2v1zm1-9h1V4H2v1h1v3zm-1 3h1.8L2 13.1v.9h3v-1H3.2L5 10.9V10H2v1zm5-6v2h14V5H7zm0 14h14v-2H7v2zm0-6h14v-2H7v2z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('blockquote')" title="Blockquote" @click="editor.chain().focus().toggleBlockquote().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 17h3l2-4V7H5v6h3zm8 0h3l2-4V7h-6v6h3z"/></svg>
      </ToolBtn>
      <ToolBtn :active="editor.isActive('codeBlock')" title="Code block" @click="editor.chain().focus().toggleCodeBlock().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20 3H4v10c0 2.21 1.79 4 4 4h6c2.21 0 4-1.79 4-4v-3h2c1.11 0 2-.89 2-2V5c0-1.11-.89-2-2-2zm0 5h-2V5h2v3zM4 19h16v2H4z"/></svg>
      </ToolBtn>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-0.5">
      <ToolBtn title="Undo (Ctrl+Z)" @click="editor.chain().focus().undo().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>
      </ToolBtn>
      <ToolBtn title="Redo (Ctrl+Y)" @click="editor.chain().focus().redo().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/></svg>
      </ToolBtn>
      <ToolBtn title="Horizontal rule" @click="editor.chain().focus().setHorizontalRule().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
      </ToolBtn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h } from 'vue'
import type { Editor } from '@tiptap/vue-3'

const props = defineProps<{ editor: Editor }>()

// Inline ToolBtn component
const ToolBtn = defineComponent({
  props: { active: Boolean, title: String },
  emits: ['click'],
  setup(p, { slots, emit }) {
    return () =>
      h('button', {
        title: p.title,
        class: [
          'w-7 h-7 flex items-center justify-center rounded transition-colors',
          p.active
            ? 'bg-primary-100 text-primary-700'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
        ],
        onClick: () => emit('click'),
        type: 'button',
      }, slots.default?.())
  },
})

function setHeading(e: Event) {
  const level = parseInt((e.target as HTMLSelectElement).value)
  if (level === 0) {
    props.editor.chain().focus().setParagraph().run()
  } else {
    props.editor.chain().focus().toggleHeading({ level: level as 1|2|3 }).run()
  }
}
</script>
