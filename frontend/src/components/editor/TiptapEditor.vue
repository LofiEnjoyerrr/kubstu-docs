<template>
  <div class="flex flex-col flex-1 overflow-hidden bg-slate-100">
    <EditorToolbar
      v-if="editor && editable"
      :editor="editor"
      :doc-id="docId"
      :doc-title="docTitle"
      :page-layout="pageLayout"
      :show-page-numbers="showPageNumbers"
      :page-number-start="pageNumberStart"
      :header-active="headerActive"
      :footer-active="footerActive"
      :header-json="latestHeaderJson"
      :footer-json="latestFooterJson"
      :paragraph-attrs="currentParagraphAttrs"
      @docx-imported="payload => emit('docxImported', payload)"
      @update-page-layout="layout => emit('updatePageLayout', layout)"
      @toggle-header="toggleHeader"
      @toggle-footer="toggleFooter"
      @set-page-numbers="v => emit('updatePageLayout', { show_page_numbers: v })"
      @set-page-number-start="v => emit('updatePageLayout', { page_number_start: v })"
      @set-paragraph-attr="onSetParagraphAttr"
    />

    <div class="flex-1 overflow-y-auto">
      <!-- Outer "paper" container — width = page width -->
      <div class="mx-auto my-8 transition-[width] duration-150" :style="paperWrapperStyle">
        <!-- HEADER band -->
        <div
          v-if="headerVisible"
          class="bg-white shadow-sm rounded-t-md border-b border-dashed border-slate-200"
          :style="bandStyle"
        >
          <div class="text-[10px] uppercase tracking-wider text-slate-400 px-1 pt-1">Header</div>
          <EditorContent
            :editor="headerEditor"
            class="tiptap-mini focus:outline-none px-1"
          />
        </div>

        <!-- MAIN page -->
        <div
          class="bg-white shadow-lg"
          :class="[headerVisible ? '' : 'rounded-t-md', footerVisible ? '' : 'rounded-b-md']"
          :style="mainStyle"
        >
          <EditorContent :editor="editor" class="tiptap-editor focus:outline-none min-h-[60vh]" />
        </div>

        <!-- FOOTER band -->
        <div
          v-if="footerVisible"
          class="bg-white shadow-sm rounded-b-md border-t border-dashed border-slate-200"
          :style="bandStyle"
        >
          <EditorContent
            :editor="footerEditor"
            class="tiptap-mini focus:outline-none px-1"
          />
          <div class="text-[10px] uppercase tracking-wider text-slate-400 px-1 pb-1 text-right">
            Footer · Page {{ firstPageNumber }} of {{ pageCount }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, computed, onBeforeUnmount, ref, nextTick } from 'vue'
import { useEditor, EditorContent, Editor } from '@tiptap/vue-3'
import { Extension, Editor as CoreEditor } from '@tiptap/core'
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
import { ParagraphSpacing } from './ParagraphSpacing'
import { PageBreak } from './PageBreak'
import { PageNumber } from './PageNumber'
import { paginate } from './paginate'
import apiClient from '../../api/client'
import { resolveMediaUrl } from '../../utils/media'
import type { PageLayout } from '../../types'

const props = defineProps<{
  modelValue: unknown
  editable?: boolean
  docId?: number
  docTitle?: string
  pageLayout: PageLayout
  headerContent?: string
  footerContent?: string
  showPageNumbers?: boolean
  pageNumberStart?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  selectionUpdate: [from: number, to: number, text: string]
  commentPositionsChanged: [payload: { updated: Array<{ id: number; from: number; to: number; quote: string }>; deleted: number[] }]
  docxImported: [payload: { content: unknown }]
  updatePageLayout: [layout: Partial<PageLayout> & {
    header_content?: string
    footer_content?: string
    show_page_numbers?: boolean
    page_number_start?: number
  }]
  updateHeaderContent: [json: unknown]
  updateFooterContent: [json: unknown]
}>()

let isRemoteUpdate = false
let storedCommentMarks: CommentMark[] = []
let lastEmittedJson = ''
let lastReportedMarksJson = ''

// ── shared extensions builder ───────────────────────────────────────────────

function baseExtensions(opts: { placeholder?: string } = {}) {
  return [
    StarterKit,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Image.configure({ inline: false, allowBase64: true }),
    Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
    Placeholder.configure({ placeholder: opts.placeholder ?? 'Start writing your document…' }),
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
    Subscript,
    Superscript,
    FontSize,
    FontFamily,
    LineHeight,
    ParagraphSpacing,
    PageNumber,
  ]
}

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

// ── main editor ─────────────────────────────────────────────────────────────

const editor = useEditor({
  editable: props.editable ?? true,
  extensions: [
    ...baseExtensions(),
    Table.configure({ resizable: true, allowTableNodeSelection: true }),
    TableRow,
    TableHeader,
    TableCell,
    TaskList,
    TaskItem.configure({ nested: true }),
    PageBreak,
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
    refreshParagraphAttrs(editor)
  },
  onTransaction: ({ editor, transaction }) => {
    if (isRemoteUpdate) return
    if (!transaction.docChanged) return

    refreshParagraphAttrs(editor)
    refreshPagination(editor)

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

// ── header / footer mini editors ────────────────────────────────────────────

const headerActive = ref(false)
const footerActive = ref(false)

const latestHeaderJson = ref<unknown>(parseBandContent(props.headerContent))
const latestFooterJson = ref<unknown>(parseBandContent(props.footerContent))

function makeBandEditor(initial: unknown, placeholder: string, onUpdate: (json: unknown) => void): Editor {
  return new Editor({
    editable: props.editable ?? true,
    extensions: baseExtensions({ placeholder }),
    content: normalizeContent(initial),
    onUpdate: ({ editor }) => {
      const json = editor.getJSON()
      onUpdate(json)
      if (placeholder.toLowerCase().includes('header')) latestHeaderJson.value = json
      else latestFooterJson.value = json
    },
    onFocus: () => {
      if (placeholder.toLowerCase().includes('header')) headerActive.value = true
      else footerActive.value = true
    },
    onBlur: () => {
      headerActive.value = false
      footerActive.value = false
    },
  })
}

const headerEditor = makeBandEditor(
  parseBandContent(props.headerContent),
  'Header (page number, title, …)',
  json => emit('updateHeaderContent', json),
)

const footerEditor = makeBandEditor(
  parseBandContent(props.footerContent),
  'Footer (page number, date, …)',
  json => emit('updateFooterContent', json),
)

function parseBandContent(s: string | undefined): unknown {
  if (!s) return null
  try { return JSON.parse(s) } catch { return null }
}

// ── pagination + per-page numbers ───────────────────────────────────────────

const pageCount = ref(1)
const firstPageNumber = ref(1)

function refreshPagination(ed: CoreEditor | Editor) {
  const info = paginate(ed.getJSON() as any, props.pageNumberStart ?? 1)
  pageCount.value = info.pageCount
  firstPageNumber.value = info.pageNumbers[0] ?? 1
  updatePageNumberChipLabels()
}

function updatePageNumberChipLabels() {
  // Rewrite each page-number-chip label so the user sees a real number,
  // not a "#" placeholder. We use textContent on the header/footer DOM
  // so this stays out of the editor's transaction history.
  const fmt = (n: number) => String(n)
  for (const ed of [headerEditor, footerEditor]) {
    const root = ed.view?.dom as HTMLElement | undefined
    if (!root) continue
    root.querySelectorAll('[data-page-number]').forEach((el) => {
      const kind = (el as HTMLElement).dataset.kind ?? 'number'
      if (kind === 'count') (el as HTMLElement).textContent = fmt(pageCount.value)
      else (el as HTMLElement).textContent = fmt(firstPageNumber.value)
    })
  }
}

// ── current paragraph attrs (margin/indent) for toolbar bindings ────────────

const currentParagraphAttrs = ref<{
  marginTop: string
  marginBottom: string
  marginLeft: string
  marginRight: string
  textIndent: string
}>({
  marginTop: '', marginBottom: '', marginLeft: '', marginRight: '', textIndent: '',
})

function refreshParagraphAttrs(ed: CoreEditor | Editor) {
  const a = (
    ed.getAttributes('paragraph')
    || ed.getAttributes('heading')
    || {}
  ) as Record<string, string>
  currentParagraphAttrs.value = {
    marginTop: a.marginTop ?? '',
    marginBottom: a.marginBottom ?? '',
    marginLeft: a.marginLeft ?? '',
    marginRight: a.marginRight ?? '',
    textIndent: a.textIndent ?? '',
  }
}

function onSetParagraphAttr(which: 'marginTop' | 'marginRight' | 'marginBottom' | 'marginLeft' | 'textIndent', value: string) {
  if (!editor.value) return
  const chain = editor.value.chain().focus()
  const v = value.trim() === '' ? '' : value
  if (which === 'textIndent') {
    chain.setParagraphTextIndent(v).run()
  } else {
    const dir = which.replace(/^margin/, '').toLowerCase() as 'top' | 'right' | 'bottom' | 'left'
    chain.setParagraphMargin(dir, v).run()
  }
}

// ── page layout styling ─────────────────────────────────────────────────────

const paperWrapperStyle = computed(() => ({
  width: `${props.pageLayout.page_width}px`,
}))

const mainStyle = computed(() => ({
  paddingTop: `${props.pageLayout.margin_top}px`,
  paddingRight: `${props.pageLayout.margin_right}px`,
  paddingBottom: `${props.pageLayout.margin_bottom}px`,
  paddingLeft: `${props.pageLayout.margin_left}px`,
  minHeight: `${props.pageLayout.page_height}px`,
  boxSizing: 'border-box' as const,
}))

const bandStyle = computed(() => ({
  paddingLeft: `${props.pageLayout.margin_left}px`,
  paddingRight: `${props.pageLayout.margin_right}px`,
  paddingTop: `${Math.round(props.pageLayout.margin_top / 3)}px`,
  paddingBottom: `${Math.round(props.pageLayout.margin_top / 3)}px`,
}))

const headerVisible = computed(() =>
  // Visible when the document has header content OR when the user explicitly
  // toggled it on for editing.
  headerActive.value || hasContent(props.headerContent),
)

const footerVisible = computed(() =>
  footerActive.value || hasContent(props.footerContent) || (props.showPageNumbers ?? false),
)

function hasContent(s: string | undefined): boolean {
  if (!s) return false
  try {
    const v = JSON.parse(s)
    if (!v?.content?.length) return false
    // Treat a single empty paragraph as "empty".
    return v.content.some((n: any) =>
      (n.content && n.content.length > 0) || (n.type !== 'paragraph'),
    )
  } catch {
    return false
  }
}

function toggleHeader() {
  headerActive.value = !headerActive.value
  if (headerActive.value) {
    nextTick(() => headerEditor.commands.focus())
  }
}

function toggleFooter() {
  footerActive.value = !footerActive.value
  if (footerActive.value) {
    nextTick(() => footerEditor.commands.focus())
  }
}

// ── image upload ────────────────────────────────────────────────────────────

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

// ── helpers ─────────────────────────────────────────────────────────────────

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
  refreshPagination(editor.value)

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

function applyRemoteHeader(content: unknown) {
  headerEditor.commands.setContent(normalizeContent(content) as string, false)
}

function applyRemoteFooter(content: unknown) {
  footerEditor.commands.setContent(normalizeContent(content) as string, false)
}

// ── watchers ────────────────────────────────────────────────────────────────

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
  (val) => {
    editor.value?.setEditable(val ?? true)
    headerEditor.setEditable(val ?? true)
    footerEditor.setEditable(val ?? true)
  },
)

watch(() => props.pageNumberStart, () => {
  if (editor.value) refreshPagination(editor.value)
})

// Update header/footer chip labels whenever pagination or content changes.
watch(pageCount, () => updatePageNumberChipLabels())
watch(firstPageNumber, () => updatePageNumberChipLabels())

defineExpose({
  applyRemote,
  applyRemoteHeader,
  applyRemoteFooter,
  updateCursor,
  clearCursor,
  setComments,
  jumpTo,
})

onBeforeUnmount(() => {
  editor.value?.destroy()
  headerEditor.destroy()
  footerEditor.destroy()
})
</script>

<style>
/* Find & replace highlights */
.find-match {
  background: rgba(250, 204, 21, 0.45);
  border-radius: 2px;
}
.find-match-active {
  background: rgba(249, 115, 22, 0.65);
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.5);
}

/* Page break visual */
.tiptap-editor .page-break {
  position: relative;
  display: block;
  margin: 32px -16px;
  border-top: 2px dashed #94a3b8;
  user-select: none;
}
.tiptap-editor .page-break .page-break-label {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  padding: 1px 10px;
  font-size: 11px;
  color: #475569;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.tiptap-editor .page-break.ProseMirror-selectednode {
  border-top-color: #2563eb;
}

/* Page number chip */
.tiptap-editor .page-number-chip,
.tiptap-mini .page-number-chip {
  display: inline-block;
  padding: 0 4px;
  background: #e0e7ff;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
  font-size: 0.9em;
  color: #3730a3;
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
.tiptap-editor mark,
.tiptap-mini mark {
  padding: 0 2px;
  border-radius: 2px;
}

/* Header / footer mini editors */
.tiptap-mini {
  min-height: 1.6em;
  font-size: 0.9rem;
  color: #475569;
}
.tiptap-mini p { margin: 0.25rem 0; }
.tiptap-mini p.is-editor-empty:first-child::before {
  content: attr(data-placeholder);
  color: #94a3b8;
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
