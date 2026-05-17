<template>
  <div class="flex flex-wrap items-center gap-0.5 px-2 py-1 border-b border-slate-200 bg-white select-none">

    <!-- ── Font family ───────────────────────────────────────────── -->
    <select
      :value="currentFontFamily"
      class="toolbar-select w-36"
      title="Font family"
      @change="e => applyFontFamily((e.target as HTMLSelectElement).value)"
    >
      <option value="">Default font</option>
      <option v-for="f in FONTS" :key="f" :value="f" :style="{ fontFamily: f }">{{ f }}</option>
    </select>

    <!-- ── Font size ─────────────────────────────────────────────── -->
    <select
      :value="currentFontSize"
      class="toolbar-select w-16"
      title="Font size"
      @change="e => applyFontSize((e.target as HTMLSelectElement).value)"
    >
      <option value="">Size</option>
      <option v-for="s in SIZES" :key="s" :value="`${s}px`">{{ s }}</option>
    </select>

    <Sep />

    <!-- ── Block style ───────────────────────────────────────────── -->
    <select
      :value="currentHeading"
      class="toolbar-select w-28"
      @change="setHeading"
    >
      <option value="0">Paragraph</option>
      <option value="1">Heading 1</option>
      <option value="2">Heading 2</option>
      <option value="3">Heading 3</option>
    </select>

    <Sep />

    <!-- ── Inline formatting ─────────────────────────────────────── -->
    <Btn :active="editor.isActive('bold')"      title="Bold (Ctrl+B)"      @click="editor.chain().focus().toggleBold().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15.6 11.8A4 4 0 0013 5H7v14h6.5a4.5 4.5 0 002.1-8.2zM9 7h4a2 2 0 010 4H9V7zm4.5 10H9v-4h4.5a2.5 2.5 0 010 5z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('italic')"    title="Italic (Ctrl+I)"    @click="editor.chain().focus().toggleItalic().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4v3h2.21l-3.42 8H6v3h8v-3h-2.21l3.42-8H18V4z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('underline')" title="Underline (Ctrl+U)" @click="editor.chain().focus().toggleUnderline().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 17c3.31 0 6-2.69 6-6V3h-2.5v8c0 1.93-1.57 3.5-3.5 3.5S8.5 12.93 8.5 11V3H6v8c0 3.31 2.69 6 6 6zm-7 2v2h14v-2H5z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('strike')"    title="Strikethrough"      @click="editor.chain().focus().toggleStrike().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 19h4v-3h-4v3zM5 4v3h5v3h4V7h5V4H5zM3 14h18v-2H3v2z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('code')"      title="Inline code"        @click="editor.chain().focus().toggleCode().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
    </Btn>

    <!-- Text color -->
    <label class="w-7 h-7 flex items-center justify-center rounded cursor-pointer hover:bg-slate-100 transition-colors relative" title="Text color">
      <span class="flex flex-col items-center gap-px">
        <span class="text-[11px] font-bold text-slate-700 leading-none">A</span>
        <span class="w-4 h-1 rounded-sm" :style="{ background: currentColor }" />
      </span>
      <input type="color" :value="currentColor" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" @input="e => applyColor((e.target as HTMLInputElement).value)" />
    </label>

    <Sep />

    <!-- ── Alignment ─────────────────────────────────────────────── -->
    <Btn :active="editor.isActive({ textAlign: 'left' })"    title="Align left"   @click="editor.chain().focus().setTextAlign('left').run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15 15H3v2h12v-2zm0-8H3v2h12V7zM3 13h18v-2H3v2zm0 8h18v-2H3v2zM3 3v2h18V3H3z"/></svg>
    </Btn>
    <Btn :active="editor.isActive({ textAlign: 'center' })"  title="Center"       @click="editor.chain().focus().setTextAlign('center').run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M7 15v2h10v-2H7zm-4 6h18v-2H3v2zm0-8h18v-2H3v2zm4-6v2h10V7H7zM3 3v2h18V3H3z"/></svg>
    </Btn>
    <Btn :active="editor.isActive({ textAlign: 'right' })"   title="Align right"  @click="editor.chain().focus().setTextAlign('right').run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zm6-4h12v-2H9v2zm-6-4h18v-2H3v2zm6-4h12V7H9v2zM3 3v2h18V3H3z"/></svg>
    </Btn>

    <Sep />

    <!-- ── Lists + Indent ────────────────────────────────────────── -->
    <Btn :active="editor.isActive('bulletList')"  title="Bullet list"                @click="editor.chain().focus().toggleBulletList().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('orderedList')" title="Numbered list"              @click="editor.chain().focus().toggleOrderedList().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M2 17h2v.5H3v1h1v.5H2v1h3v-4H2v1zm1-9h1V4H2v1h1v3zm-1 3h1.8L2 13.1v.9h3v-1H3.2L5 10.9V10H2v1zm5-6v2h14V5H7zm0 14h14v-2H7v2zm0-6h14v-2H7v2z"/></svg>
    </Btn>
    <Btn title="Increase indent (Tab)"    @click="editor.chain().focus().sinkListItem('listItem').run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zm0-4h12v-2H3v2zm0-4h18v-2H3v2zm0-4h12V7H3v2zm0-6v2h18V3H3zM21 7l-4 4 4 4V7z" transform="scale(-1,1) translate(-24,0)"/><path d="M3 5v14l4-7z"/><rect x="9" y="7" width="12" height="2"/><rect x="9" y="11" width="9" height="2"/><rect x="9" y="15" width="12" height="2"/></svg>
    </Btn>
    <Btn title="Decrease indent (Shift+Tab)" @click="editor.chain().focus().liftListItem('listItem').run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 5v14l4-7z" transform="scale(-1,1) translate(-24,0)"/><rect x="3" y="7" width="12" height="2"/><rect x="3" y="11" width="9" height="2"/><rect x="3" y="15" width="12" height="2"/></svg>
    </Btn>

    <Sep />

    <!-- ── Block elements ────────────────────────────────────────── -->
    <Btn :active="editor.isActive('blockquote')" title="Blockquote" @click="editor.chain().focus().toggleBlockquote().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 17h3l2-4V7H5v6h3zm8 0h3l2-4V7h-6v6h3z"/></svg>
    </Btn>
    <Btn :active="editor.isActive('codeBlock')"  title="Code block" @click="editor.chain().focus().toggleCodeBlock().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20 3H4v10c0 2.21 1.79 4 4 4h6c2.21 0 4-1.79 4-4v-3h2c1.11 0 2-.89 2-2V5c0-1.11-.89-2-2-2zm0 5h-2V5h2v3zM4 19h16v2H4z"/></svg>
    </Btn>

    <Sep />

    <!-- ── Image ─────────────────────────────────────────────────── -->
    <input ref="imageInputRef" type="file" accept="image/*" class="sr-only" @change="onImageSelected" />
    <Btn title="Insert image" @click="imageInputRef?.click()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
    </Btn>

    <Sep />

    <!-- ── History + HR ──────────────────────────────────────────── -->
    <Btn title="Undo (Ctrl+Z)" @click="editor.chain().focus().undo().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>
    </Btn>
    <Btn title="Redo (Ctrl+Y)" @click="editor.chain().focus().redo().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/></svg>
    </Btn>
    <Btn title="Horizontal rule" @click="editor.chain().focus().setHorizontalRule().run()">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
    </Btn>

    <Sep />

    <!-- ── DOCX import / export ──────────────────────────────────── -->
    <input
      ref="docxInputRef"
      type="file"
      accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      class="sr-only"
      @change="onDocxImport"
    />
    <Btn title="Import DOCX" :disabled="isImporting" @click="docxInputRef?.click()">
      <svg v-if="!isImporting" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
      <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
    </Btn>
    <Btn title="Export as DOCX" :disabled="isExporting" @click="onDocxExport">
      <svg v-if="!isExporting" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L11 14.17V7h2v7.17l2.59-2.58L17 13l-5 5z"/></svg>
      <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
    </Btn>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineComponent, h } from 'vue'
import type { Editor } from '@tiptap/vue-3'
import apiClient from '../../api/client'
import { resolveMediaUrl } from '../../utils/media'

const props = defineProps<{
  editor: Editor
  docId?: number
  docTitle?: string
}>()

const emit = defineEmits<{ docxImported: [] }>()

// ── constants ─────────────────────────────────────────────────────────────────

const FONTS = [
  'Arial',
  'Times New Roman',
  'Courier New',
  'Georgia',
  'Verdana',
  'Trebuchet MS',
  'Comic Sans MS',
  'Impact',
]

const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 40, 48, 60, 72]

// ── reactive state ────────────────────────────────────────────────────────────

const imageInputRef = ref<HTMLInputElement | null>(null)
const docxInputRef  = ref<HTMLInputElement | null>(null)
const isImporting   = ref(false)
const isExporting   = ref(false)

// ── computed from editor state ────────────────────────────────────────────────

const currentFontFamily = computed(() =>
  props.editor.getAttributes('textStyle').fontFamily ?? '',
)

const currentFontSize = computed(() =>
  props.editor.getAttributes('textStyle').fontSize ?? '',
)

const currentColor = computed(() =>
  props.editor.getAttributes('textStyle').color ?? '#000000',
)

const currentHeading = computed(() => {
  if (props.editor.isActive('heading', { level: 1 })) return '1'
  if (props.editor.isActive('heading', { level: 2 })) return '2'
  if (props.editor.isActive('heading', { level: 3 })) return '3'
  return '0'
})

// ── formatting commands ───────────────────────────────────────────────────────

function applyFontFamily(value: string) {
  if (value) {
    props.editor.chain().focus().setFontFamily(value).run()
  } else {
    props.editor.chain().focus().unsetFontFamily().run()
  }
}

function applyFontSize(value: string) {
  if (value) {
    props.editor.chain().focus().setFontSize(value).run()
  } else {
    props.editor.chain().focus().unsetFontSize().run()
  }
}

function applyColor(value: string) {
  props.editor.chain().focus().setColor(value).run()
}

function setHeading(e: Event) {
  const level = parseInt((e.target as HTMLSelectElement).value)
  if (level === 0) {
    props.editor.chain().focus().setParagraph().run()
  } else {
    props.editor.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 }).run()
  }
}

// ── image upload ──────────────────────────────────────────────────────────────

async function onImageSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !props.docId) return
  if (imageInputRef.value) imageInputRef.value.value = ''

  try {
    const formData = new FormData()
    formData.append('image', file)
    const { data } = await apiClient.post<{ url: string }>(
      `/api/docs/${props.docId}/images/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    const src = resolveMediaUrl(data.url) ?? data.url
    props.editor.chain().focus().setImage({ src }).run()
  } catch (err) {
    console.error('Image upload failed', err)
  }
}

// ── DOCX ──────────────────────────────────────────────────────────────────────

/**
 * Normalise the HTML that mammoth produces so that Tiptap's extensions
 * can reliably parse it:
 *
 * 1. Convert deprecated `align="..."` attributes to `style="text-align:…"`.
 *    Some Word files / mammoth versions still emit the HTML4 attribute.
 * 2. Ensure every block with an explicit `text-align` has it as an inline
 *    style so Tiptap's TextAlign globalAttribute `parseHTML` callback can
 *    read `element.style.textAlign`.
 */
function normalizeMammothHtml(html: string): string {
  try {
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')

    doc.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, blockquote').forEach(rawEl => {
      const el = rawEl as HTMLElement

      // 1. Migrate `align="center"` → `style="text-align: center"`
      const alignAttr = el.getAttribute('align')
      if (alignAttr) {
        if (!el.style.textAlign) el.style.textAlign = alignAttr
        el.removeAttribute('align')
      }

      // 2. If a text-align is already in the style string but the browser
      //    normalised it to a different casing, re-write it explicitly so
      //    Tiptap's `element.style.textAlign` lookup returns a non-empty string.
      const ta = el.style.textAlign
      if (ta && ta !== 'left') {
        // Re-assign to ensure the property is set (handles some browser quirks)
        el.style.textAlign = ta
      }
    })

    return doc.body.innerHTML
  } catch {
    return html // fall back to raw html on any parsing error
  }
}

async function onDocxImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (docxInputRef.value) docxInputRef.value.value = ''

  isImporting.value = true
  try {
    const mammoth = await import('mammoth')
    const arrayBuffer = await file.arrayBuffer()

    const result = await mammoth.convertToHtml(
      { arrayBuffer },
      {
        // Embed each image as a base64 data-URI so Tiptap can display it.
        convertImage: mammoth.images.imgElement((image: any) =>
          image.read('base64').then((data: string) => ({
            src: `data:${image.contentType};base64,${data}`,
          })),
        ),
        // Map common Word paragraph / run styles to their HTML equivalents.
        styleMap: [
          "p[style-name='Heading 1'] => h1:fresh",
          "p[style-name='Heading 2'] => h2:fresh",
          "p[style-name='Heading 3'] => h3:fresh",
          "p[style-name='Heading 4'] => h4:fresh",
          "p[style-name='Heading 5'] => h5:fresh",
          "p[style-name='Heading 6'] => h6:fresh",
          "p[style-name='Quote']         => blockquote > p:fresh",
          "p[style-name='Intense Quote'] => blockquote > p:fresh",
          "r[style-name='Strong']    => strong",
          "r[style-name='Emphasis']  => em",
          "r[style-name='Underline'] => u",
          "r[style-name='Strikethrough'] => s",
          "p[style-name='List Paragraph'] => li:fresh",
          "p[style-name='Code'] => pre > code:fresh",
        ],
      },
    )

    props.editor.commands.setContent(normalizeMammothHtml(result.value))
    emit('docxImported')
  } catch (err) {
    console.error('DOCX import failed', err)
  } finally {
    isImporting.value = false
  }
}

async function onDocxExport() {
  isExporting.value = true
  try {
    const { exportToDocx } = await import('../../utils/docxExport')
    await exportToDocx(props.editor.getJSON(), props.docTitle ?? 'document')
  } catch (err) {
    console.error('DOCX export failed', err)
  } finally {
    isExporting.value = false
  }
}

// ── sub-components ────────────────────────────────────────────────────────────

const Btn = defineComponent({
  props: { active: Boolean, title: String, disabled: Boolean },
  emits: ['click'],
  setup(p, { slots, emit }) {
    return () =>
      h('button', {
        type: 'button',
        title: p.title,
        disabled: p.disabled,
        class: [
          'w-7 h-7 flex items-center justify-center rounded transition-colors',
          p.disabled
            ? 'text-slate-300 cursor-not-allowed'
            : p.active
            ? 'bg-primary-100 text-primary-700'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
        ],
        onClick: () => !p.disabled && emit('click'),
      }, slots.default?.())
  },
})

const Sep = defineComponent({
  setup: () => () => h('div', { class: 'w-px h-5 bg-slate-200 mx-0.5 shrink-0' }),
})
</script>

<style scoped>
.toolbar-select {
  @apply h-7 px-1.5 rounded text-xs border border-slate-200 text-slate-700 bg-white focus:outline-none focus:border-primary-400;
}
</style>
