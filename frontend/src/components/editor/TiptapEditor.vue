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
      :header-active="headerOpen"
      :footer-active="footerOpen"
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
      <div class="mx-auto my-8 paper-stack" :style="paperWrapperStyle">
        <!-- HEADER band for the first page -->
        <div
          v-if="headerVisible"
          class="paper-band paper-band-top"
          :style="bandStyle"
          @dblclick="activateHeader"
        >
          <div class="paper-band-label">
            Верхний колонтитул · стр. {{ firstPageNumber }} из {{ pageCount }}
            <button
              v-if="headerOpen"
              type="button"
              class="paper-band-close"
              title="Закрыть верхний колонтитул"
              @click.stop="closeHeader"
            >✕</button>
          </div>
          <EditorContent
            :editor="headerEditor"
            class="tiptap-mini focus:outline-none px-1"
          />
        </div>
        <!-- Sentinel: dbl-click on the empty top margin opens the header -->
        <div
          v-else
          class="paper-band-sentinel paper-band-sentinel-top"
          :style="sentinelStyle"
          title="Двойной клик — добавить верхний колонтитул"
          @dblclick="activateHeader"
        />

        <!-- MAIN paper — one tall sheet visually broken by page/section breaks -->
        <div
          class="bg-white shadow-lg paper-body"
          :class="[headerVisible ? '' : 'rounded-t-md', footerVisible ? '' : 'rounded-b-md']"
          :style="mainStyle"
        >
          <EditorContent :editor="editor" class="tiptap-editor focus:outline-none min-h-[60vh]" />
        </div>

        <!-- FOOTER band for the last page -->
        <div
          v-if="footerVisible"
          class="paper-band paper-band-bottom"
          :style="bandStyle"
          @dblclick="activateFooter"
        >
          <EditorContent
            :editor="footerEditor"
            class="tiptap-mini focus:outline-none px-1"
          />
          <div class="paper-band-label paper-band-label-bottom">
            Нижний колонтитул · стр. {{ lastPageNumber }} из {{ pageCount }}
            <button
              v-if="footerOpen"
              type="button"
              class="paper-band-close"
              title="Закрыть нижний колонтитул"
              @click.stop="closeFooter"
            >✕</button>
          </div>
        </div>
        <div
          v-else
          class="paper-band-sentinel paper-band-sentinel-bottom"
          :style="sentinelStyle"
          title="Двойной клик — добавить нижний колонтитул"
          @dblclick="activateFooter"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, computed, onBeforeUnmount, onMounted, ref, nextTick } from 'vue'
import { useEditor, EditorContent, Editor } from '@tiptap/vue-3'
import { Extension, Editor as CoreEditor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { ResolvedImage } from './ResolvedImage'
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
import { SectionBreak } from './SectionBreak'
import { PageNumber } from './PageNumber'
import { AutoPagination, autoPaginationKey, getAutoBreakPositions } from './AutoPagination'
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

/**
 * Available content height per page in CSS pixels — i.e. the paper height
 * minus the top and bottom margins. The auto-pagination plugin uses this
 * to decide when to flow content onto a new page.
 */
function computePageContentHeight(pl: PageLayout): number {
  return Math.max(100, pl.page_height - pl.margin_top - pl.margin_bottom)
}

// ── shared extensions builder ───────────────────────────────────────────────

function baseExtensions(opts: { placeholder?: string } = {}) {
  return [
    StarterKit,
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    ResolvedImage.configure({ inline: false, allowBase64: true }),
    Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
    Placeholder.configure({ placeholder: opts.placeholder ?? 'Начните вводить текст документа…' }),
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
    SectionBreak,
    AutoPagination.configure({
      pageHeight: computePageContentHeight(props.pageLayout),
    }),
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

    // The AutoPagination plugin dispatches meta-only transactions when
    // the computed break positions change — those don't bump ``docChanged``
    // but they DO change the page count, so we still need to refresh.
    const autoBreakChanged = transaction.getMeta(autoPaginationKey) !== undefined
    if (!transaction.docChanged && !autoBreakChanged) return

    refreshParagraphAttrs(editor)
    refreshPagination(editor)

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

// ── header / footer mini editors ────────────────────────────────────────────

// Tri-state user choice for header/footer visibility. ``null`` means the
// user hasn't yet expressed a preference — in that case we fall back to
// "is there any content in the band?" so existing docs open with their
// header/footer visible. Once the user explicitly toggles, we honor that
// choice and ignore the content-presence default. This is what fixes the
// long-standing bug where "Close header" did nothing after typing
// because the visibility was hard-tied to ``hasContent``.
const headerExplicit = ref<boolean | null>(null)
const footerExplicit = ref<boolean | null>(null)

const latestHeaderJson = ref<unknown>(parseBandContent(props.headerContent))
const latestFooterJson = ref<unknown>(parseBandContent(props.footerContent))

function makeBandEditor(
  initial: unknown,
  placeholder: string,
  kind: 'header' | 'footer',
  onUpdate: (json: unknown) => void,
): Editor {
  return new Editor({
    editable: props.editable ?? true,
    extensions: baseExtensions({ placeholder }),
    content: normalizeContent(initial),
    onUpdate: ({ editor }) => {
      const json = editor.getJSON()
      onUpdate(json)
      if (kind === 'header') latestHeaderJson.value = json
      else latestFooterJson.value = json
    },
  })
}

const headerEditor = makeBandEditor(
  parseBandContent(props.headerContent),
  'Верхний колонтитул (номер страницы, заголовок, …)',
  'header',
  json => emit('updateHeaderContent', json),
)

const footerEditor = makeBandEditor(
  parseBandContent(props.footerContent),
  'Нижний колонтитул (номер страницы, дата, …)',
  'footer',
  json => emit('updateFooterContent', json),
)

function parseBandContent(s: string | undefined): unknown {
  if (!s) return null
  try { return JSON.parse(s) } catch { return null }
}

// ── pagination + per-page numbers ───────────────────────────────────────────

const pageCount = ref(1)
const firstPageNumber = ref(1)
const lastPageNumber = ref(1)
const pageNumbersByIdx = ref<number[]>([1])

function refreshPagination(ed: CoreEditor | Editor) {
  const info = paginate(
    ed.state,
    props.pageNumberStart ?? 1,
    getAutoBreakPositions(ed.state),
  )
  pageCount.value = info.pageCount
  firstPageNumber.value = info.pageNumbers[0] ?? 1
  lastPageNumber.value = info.pageNumbers[info.pageNumbers.length - 1] ?? 1
  pageNumbersByIdx.value = info.pageNumbers
  // Update labels in mini editors and in the in-body page-break previews.
  nextTick(() => {
    updatePageNumberChipLabels()
    updatePageBreakChrome(ed)
  })
}

function updatePageNumberChipLabels() {
  // Rewrite each page-number-chip label so the user sees a real number,
  // not a "#" placeholder. We use textContent on the header/footer DOM
  // so this stays out of the editor's transaction history.
  const fmt = (n: number) => String(n)
  for (const ed of [headerEditor, footerEditor]) {
    const root = ed.view?.dom as HTMLElement | undefined
    if (!root) continue
    const isHeader = ed === headerEditor
    const visible = isHeader ? firstPageNumber.value : lastPageNumber.value
    root.querySelectorAll('[data-page-number]').forEach((el) => {
      const kind = (el as HTMLElement).dataset.kind ?? 'number'
      if (kind === 'count') (el as HTMLElement).textContent = fmt(pageCount.value)
      else (el as HTMLElement).textContent = fmt(visible)
    })
  }
}

/**
 * Walks the rendered editor DOM and decorates every page-break / section-break
 * with a label that names the page numbers on either side. This is read-only
 * eye candy so the document looks like a real stack of paper.
 */
function updatePageBreakChrome(_ed: CoreEditor | Editor) {
  // Page-break visuals are now label-free — just an empty gap with the
  // paper-edge shadows. Nothing to update here.
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
  // The page-break gap reaches the full width of the paper by using a
  // negative horizontal margin equal to the body padding. We expose those
  // paddings here so the gap can read them.
  '--page-margin-left': `${props.pageLayout.margin_left}px`,
  '--page-margin-right': `${props.pageLayout.margin_right}px`,
  '--page-bg': '#f1f5f9', // matches outer container bg (slate-100)
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
  paddingTop: `${Math.max(8, Math.round(props.pageLayout.margin_top / 3))}px`,
  paddingBottom: `${Math.max(8, Math.round(props.pageLayout.margin_top / 3))}px`,
}))

const sentinelStyle = computed(() => ({
  height: `${Math.max(24, Math.round(props.pageLayout.margin_top / 3))}px`,
}))

const headerOpen = computed(() => headerExplicit.value ?? hasContent(props.headerContent))
const footerOpen = computed(
  () => footerExplicit.value ?? (hasContent(props.footerContent) || (props.showPageNumbers ?? false)),
)

const headerVisible = computed(() => headerOpen.value)
const footerVisible = computed(() => footerOpen.value || (props.showPageNumbers ?? false))

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
  const next = !headerOpen.value
  headerExplicit.value = next
  if (next) nextTick(() => headerEditor.commands.focus())
}
function toggleFooter() {
  const next = !footerOpen.value
  footerExplicit.value = next
  if (next) nextTick(() => footerEditor.commands.focus())
}

function activateHeader() {
  headerExplicit.value = true
  nextTick(() => headerEditor.commands.focus())
}
function activateFooter() {
  footerExplicit.value = true
  nextTick(() => footerEditor.commands.focus())
}
function closeHeader() {
  headerExplicit.value = false
  editor.value?.commands.focus()
}
function closeFooter() {
  footerExplicit.value = false
  editor.value?.commands.focus()
}

// Esc inside a mini editor returns focus to the body editor and collapses
// the band (matching Word / Google Docs behaviour).
function bindMiniEscape(ed: Editor, close: () => void) {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      close()
    }
  }
  const dom = ed.view.dom as HTMLElement
  dom.addEventListener('keydown', handler)
  return () => dom.removeEventListener('keydown', handler)
}

let unbindHeaderEsc: (() => void) | null = null
let unbindFooterEsc: (() => void) | null = null

onMounted(() => {
  unbindHeaderEsc = bindMiniEscape(headerEditor, closeHeader)
  unbindFooterEsc = bindMiniEscape(footerEditor, closeFooter)
  if (editor.value) refreshPagination(editor.value)
})

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
  latestHeaderJson.value = parseBandContent(typeof content === 'string' ? content : JSON.stringify(content))
  nextTick(updatePageNumberChipLabels)
}

function applyRemoteFooter(content: unknown) {
  footerEditor.commands.setContent(normalizeContent(content) as string, false)
  latestFooterJson.value = parseBandContent(typeof content === 'string' ? content : JSON.stringify(content))
  nextTick(updatePageNumberChipLabels)
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

// When the user resizes the paper or shifts a margin we need to tell the
// auto-pagination plugin about the new available height AND let it
// re-measure block heights against the new width. Pushing a meta update
// triggers a fresh ``view.update``, which schedules a recompute.
watch(
  () => [
    props.pageLayout.page_height,
    props.pageLayout.margin_top,
    props.pageLayout.margin_bottom,
    props.pageLayout.page_width,
    props.pageLayout.margin_left,
    props.pageLayout.margin_right,
  ],
  () => {
    if (!editor.value) return
    editor.value.commands.setAutoPageHeight(computePageContentHeight(props.pageLayout))
  },
)

// Update labels whenever counts change.
watch([pageCount, firstPageNumber, lastPageNumber], () => updatePageNumberChipLabels())

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
  unbindHeaderEsc?.()
  unbindFooterEsc?.()
  editor.value?.destroy()
  headerEditor.destroy()
  footerEditor.destroy()
})
</script>

<style>
/* Remove the default browser focus outline that ProseMirror adds when the
   editor element receives focus. The transition was visible as a blue/black
   border ring whenever the user clicked into a different document. */
.tiptap-editor .ProseMirror,
.tiptap-mini .ProseMirror {
  outline: none !important;
  box-shadow: none !important;
  border: none !important;
}
.tiptap-editor .ProseMirror-focused,
.tiptap-mini .ProseMirror-focused {
  outline: none !important;
  box-shadow: none !important;
  border: none !important;
}

/* Default typography matches Word's default — Times New Roman, 12pt. This
   applies wherever the user hasn't explicitly chosen a font/size. */
.tiptap-editor,
.tiptap-mini {
  font-family: 'Times New Roman', Times, serif;
  font-size: 12pt;
}

/* ── Paper container ───────────────────────────────────────────────────── */
.paper-stack {
  position: relative;
}

/* ── Editable header/footer bands ──────────────────────────────────────── */
.paper-band {
  position: relative;
  background: #fff;
  cursor: text;
}
.paper-band-top {
  border-bottom: 1px dashed #cbd5e1;
  border-top-left-radius: 0.375rem;
  border-top-right-radius: 0.375rem;
  box-shadow: 0 -1px 2px 0 rgba(0, 0, 0, 0.04);
}
.paper-band-bottom {
  border-top: 1px dashed #cbd5e1;
  border-bottom-left-radius: 0.375rem;
  border-bottom-right-radius: 0.375rem;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
}
.paper-band-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
  padding: 2px 4px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
}
.paper-band-label-bottom {
  padding: 4px 4px 2px;
  justify-content: flex-end;
  gap: 8px;
}
.paper-band-close {
  background: transparent;
  border: 0;
  color: #94a3b8;
  width: 16px;
  height: 16px;
  border-radius: 9999px;
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
}
.paper-band-close:hover {
  background: #f1f5f9;
  color: #334155;
}

/* Sentinel hover hint for "double-click to add a header/footer". */
.paper-band-sentinel {
  position: relative;
  background: transparent;
  cursor: pointer;
  transition: background-color 0.12s ease;
}
.paper-band-sentinel:hover {
  background: rgba(255, 255, 255, 0.6);
  outline: 1px dashed rgba(148, 163, 184, 0.6);
  outline-offset: -4px;
}

/* ── Page-break + section-break: the visual "between sheets" gap ───────── */
.tiptap-editor .page-break,
.tiptap-editor .section-break {
  position: relative;
  display: block;
  /* Reach out to the very edge of the paper so the gap looks like the
     boundary between two sheets. */
  margin-left: calc(-1 * var(--page-margin-left, 96px));
  margin-right: calc(-1 * var(--page-margin-right, 96px));
  margin-top: 28px;
  margin-bottom: 28px;
  background: var(--page-bg, #f1f5f9);
  user-select: none;
}
.tiptap-editor .page-break .page-break-paper-end,
.tiptap-editor .section-break .page-break-paper-end {
  /* Bottom-edge shadow of the previous sheet. */
  height: 6px;
  background: #fff;
  box-shadow: 0 6px 8px -4px rgba(15, 23, 42, 0.18);
  position: relative;
  z-index: 1;
}
.tiptap-editor .page-break .page-break-paper-start,
.tiptap-editor .section-break .page-break-paper-start {
  /* Top-edge shadow of the next sheet. */
  height: 6px;
  background: #fff;
  box-shadow: 0 -6px 8px -4px rgba(15, 23, 42, 0.18);
  position: relative;
  z-index: 1;
}
.tiptap-editor .page-break .page-break-gap,
.tiptap-editor .section-break .page-break-gap {
  height: 56px;
  background: var(--page-bg, #f1f5f9);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.tiptap-editor .section-break .section-break-gap {
  height: 80px;
}
/* Selected manual page break gets a soft blue tint so users know
   they've clicked it. */
.tiptap-editor .page-break.ProseMirror-selectednode .page-break-paper-end,
.tiptap-editor .page-break.ProseMirror-selectednode .page-break-paper-start,
.tiptap-editor .section-break.ProseMirror-selectednode .page-break-paper-end,
.tiptap-editor .section-break.ProseMirror-selectednode .page-break-paper-start {
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.4);
}

/* When ProseMirror inserts our auto-break as a child of a <p>, browsers
   try to treat it as inline. Force block-level layout so the gutter
   always spans the full paper width. */
.tiptap-editor .auto-page-break {
  display: block !important;
}

/* Find & replace highlights */
.find-match {
  background: rgba(250, 204, 21, 0.45);
  border-radius: 2px;
}
.find-match-active {
  background: rgba(249, 115, 22, 0.65);
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.5);
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
