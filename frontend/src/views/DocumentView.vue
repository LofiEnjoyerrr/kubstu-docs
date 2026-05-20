<template>
  <div class="flex flex-col h-screen">
    <!-- Top bar -->
    <header class="fixed inset-x-0 top-14 z-30 h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-3 shadow-sm">
      <!-- Back -->
      <RouterLink to="/dashboard" class="btn-ghost btn-sm p-1.5 rounded-lg" title="Назад в личный кабинет">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </RouterLink>

      <!-- Title -->
      <div class="flex-1 flex items-center gap-2 min-w-0">
        <input
          v-if="myRole === 'owner'"
          v-model="editableTitle"
          class="flex-1 min-w-0 font-semibold text-slate-800 bg-transparent border-none outline-none focus:ring-0 text-base truncate"
          placeholder="Без названия"
          @blur="saveTitle"
          @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
        />
        <span v-else class="font-semibold text-slate-800 text-base truncate">
          {{ doc?.title || 'Без названия' }}
        </span>

        <Transition name="fade">
          <span v-if="isSaving" class="text-xs text-slate-400 shrink-0">Сохранение…</span>
          <span v-else-if="lastSaved" class="text-xs text-slate-400 shrink-0">Сохранено</span>
        </Transition>
      </div>

      <!-- Right controls -->
      <div class="flex items-center gap-2 shrink-0">
        <!-- Connection -->
        <div
          class="flex items-center gap-1.5 text-xs px-2 py-1 rounded-full"
          :class="isConnected ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'"
        >
          <div class="w-1.5 h-1.5 rounded-full" :class="isConnected ? 'bg-green-500' : 'bg-slate-400'" />
          {{ isConnected ? 'В сети' : 'Не в сети' }}
        </div>

        <!-- Viewer badge -->
        <span v-if="myRole === 'viewer'" class="badge-slate text-xs">Только просмотр</span>

        <!-- Online collaborators -->
        <div v-if="collaborators.length" class="flex -space-x-2">
          <div
            v-for="c in collaborators.slice(0, 5)"
            :key="c.user_id ?? c.username"
            class="w-7 h-7 rounded-full border-2 border-white overflow-hidden flex items-center justify-center text-white text-xs font-bold"
            :style="c.avatar ? undefined : { backgroundColor: c.color }"
            :title="c.username"
          >
            <img
              v-if="c.avatar"
              :src="resolveMediaUrl(c.avatar)!"
              :alt="c.username"
              class="w-full h-full object-cover"
            />
            <template v-else>{{ c.username[0].toUpperCase() }}</template>
          </div>
          <div
            v-if="collaborators.length > 5"
            class="w-7 h-7 rounded-full border-2 border-white bg-slate-300 flex items-center justify-center text-slate-700 text-xs font-bold"
          >
            +{{ collaborators.length - 5 }}
          </div>
        </div>

        <!-- Add comment button — visible when text is selected -->
        <Transition name="fade">
          <button
            v-if="hasSelection && auth.isAuthenticated"
            class="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors font-medium"
            @click="openAddComment"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
            Комментарий
          </button>
        </Transition>

        <!-- Toggle comments panel -->
        <button
          class="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors"
          :class="showComments
            ? 'border-primary-300 bg-primary-50 text-primary-700'
            : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
          title="Показать/скрыть комментарии"
          @click="showComments = !showComments"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span v-if="comments.length" class="font-medium">{{ comments.length }}</span>
        </button>

        <!-- Visibility toggle -->
        <button
          v-if="myRole === 'owner' && doc"
          class="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors"
          :class="doc.is_public ? 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
          @click="togglePublic"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="doc.is_public" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          {{ doc.is_public ? 'Публичный' : 'Приватный' }}
        </button>

        <!-- Share -->
        <button v-if="myRole === 'owner'" class="btn-primary btn-sm" @click="showShare = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          Поделиться
        </button>

        <!-- Delete -->
        <button
          v-if="myRole === 'owner'"
          class="btn-sm p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50"
          title="Удалить документ"
          @click="askDelete"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Editor + optional comment sidebar -->
    <main class="flex-1 pt-28 overflow-hidden flex flex-row">
      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <svg class="w-8 h-8 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </div>

      <div v-else-if="loadError" class="flex-1 flex items-center justify-center px-4">
        <div class="text-center">
          <p class="text-slate-600 mb-4">{{ loadError }}</p>
          <RouterLink to="/dashboard" class="btn-primary">В личный кабинет</RouterLink>
        </div>
      </div>

      <template v-else>
        <TiptapEditor
          ref="editorRef"
          v-model="editorContent"
          :editable="canEdit"
          :doc-id="docId"
          :doc-title="doc?.title"
          :page-layout="pageLayout"
          :header-content="headerContent"
          :footer-content="footerContent"
          :show-page-numbers="showPageNumbers"
          :page-number-start="pageNumberStart"
          class="flex-1 min-w-0"
          @update:model-value="onEditorUpdate"
          @selection-update="onSelectionUpdate"
          @comment-positions-changed="onCommentPositionsChanged"
          @docx-imported="onDocxImported"
          @update-page-layout="onUpdatePageLayout"
          @update-header-content="onUpdateHeaderContent"
          @update-footer-content="onUpdateFooterContent"
        />

        <Transition name="slide-panel">
          <CommentPanel
            v-if="showComments"
            :comments="comments"
            :current-user-id="auth.user?.id ?? null"
            :is-owner="myRole === 'owner'"
            @close="showComments = false"
            @jump="jumpToComment"
            @delete="handleDeleteComment"
          />
        </Transition>
      </template>
    </main>

    <!-- Add comment modal -->
    <Teleport to="body">
      <div
        v-if="showAddComment"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @mousedown.self="showAddComment = false"
      >
        <div class="absolute inset-0 bg-black/40" />
        <div class="relative w-full max-w-md bg-white rounded-2xl shadow-xl p-6">
          <h2 class="font-semibold text-slate-800 mb-3">Добавить комментарий</h2>

          <div v-if="pendingQuote" class="mb-4 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg px-3 py-2">
            <p class="text-xs text-amber-700 font-medium mb-0.5">Выделенный текст</p>
            <p class="text-sm text-slate-700 line-clamp-3 italic">"{{ pendingQuote }}"</p>
          </div>

          <form @submit.prevent="submitComment">
            <textarea
              v-model="commentText"
              class="input w-full resize-none"
              rows="3"
              placeholder="Напишите комментарий…"
              autofocus
              required
            />
            <p v-if="commentError" class="error-text mt-2">{{ commentError }}</p>
            <div class="flex gap-2 justify-end mt-4">
              <button type="button" class="btn-secondary" @click="showAddComment = false">Отмена</button>
              <button type="submit" class="btn-primary" :disabled="isSubmittingComment || !commentText.trim()">
                {{ isSubmittingComment ? 'Публикация…' : 'Опубликовать' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <ShareModal
      v-if="showShare && doc"
      :doc-id="doc.id"
      :accesses="docsStore.accesses"
      @close="showShare = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useDocumentsStore } from '../stores/documents'
import { useDocumentSocket } from '../composables/useDocumentSocket'
import TiptapEditor from '../components/editor/TiptapEditor.vue'
import ShareModal from '../components/ShareModal.vue'
import CommentPanel from '../components/CommentPanel.vue'
import * as docsApi from '../api/documents'
import { resolveMediaUrl } from '../utils/media'
import type { Document, Comment, PageLayout } from '../types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const docsStore = useDocumentsStore()

const docId = computed(() => parseInt(route.params.id as string))

const doc = ref<Document | null>(null)
const isLoading = ref(true)
const loadError = ref('')
const showShare = ref(false)
const editorContent = ref<unknown>(null)
const editorRef = ref<InstanceType<typeof TiptapEditor> | null>(null)
const isSaving = ref(false)
const lastSaved = ref(false)
const editableTitle = ref('')
const myRole = ref<'owner' | 'editor' | 'viewer' | null>(null)

const pageLayout = ref<PageLayout>({
  page_width: 816,
  page_height: 1056,
  margin_top: 96,
  margin_right: 96,
  margin_bottom: 96,
  margin_left: 96,
})
const headerContent = ref<string>('')
const footerContent = ref<string>('')
const showPageNumbers = ref(false)
const pageNumberStart = ref(1)

let pageLayoutTimer: ReturnType<typeof setTimeout> | null = null
let headerSaveTimer: ReturnType<typeof setTimeout> | null = null
let footerSaveTimer: ReturnType<typeof setTimeout> | null = null

// Comments state
const comments = ref<Comment[]>([])
const showComments = ref(false)
const showAddComment = ref(false)
const commentText = ref('')
const commentError = ref('')
const isSubmittingComment = ref(false)
const pendingSelection = ref<{ from: number; to: number } | null>(null)
const pendingQuote = ref('')

let contentSaveTimer: ReturnType<typeof setTimeout> | null = null
let titleSaveTimer: ReturnType<typeof setTimeout> | null = null
let commentSyncTimer: ReturnType<typeof setTimeout> | null = null

// Pending comment position changes to send to the backend (debounced).
// Key = comment id, value = latest {from, to, quote} to PATCH.
const pendingCommentUpdates = new Map<number, { id: number; from: number; to: number; quote: string }>()
// Comment ids that collapsed to nothing and must be deleted on the backend.
const pendingCommentDeletes = new Set<number>()

const canEdit = computed(() => myRole.value === 'owner' || myRole.value === 'editor')
const hasSelection = computed(() => {
  const sel = pendingSelection.value
  return sel !== null && sel.from !== sel.to
})

const socket = useDocumentSocket(docId.value)
const { collaborators, isConnected } = socket

function applyCommentHighlights() {
  editorRef.value?.setComments(
    comments.value.map(c => ({
      id: c.id,
      from: c.from_pos,
      to: c.to_pos,
      color: c.author_color,
    })),
  )
}

onMounted(async () => {
  try {
    doc.value = await docsStore.fetchDocument(docId.value)
    editableTitle.value = doc.value.title

    // Hydrate page layout + header/footer from the document
    pageLayout.value = {
      page_width: doc.value.page_width ?? 816,
      page_height: doc.value.page_height ?? 1056,
      margin_top: doc.value.margin_top ?? 96,
      margin_right: doc.value.margin_right ?? 96,
      margin_bottom: doc.value.margin_bottom ?? 96,
      margin_left: doc.value.margin_left ?? 96,
    }
    headerContent.value = doc.value.header_content ?? ''
    footerContent.value = doc.value.footer_content ?? ''
    showPageNumbers.value = !!doc.value.show_page_numbers
    pageNumberStart.value = doc.value.page_number_start ?? 1

    try {
      editorContent.value = doc.value.content
        ? typeof doc.value.content === 'string'
          ? JSON.parse(doc.value.content)
          : doc.value.content
        : null
    } catch {
      editorContent.value = null
    }

    if (auth.isAuthenticated) {
      try {
        const res = await docsApi.getMyAccess(docId.value)
        myRole.value = res.data.role
      } catch {
        myRole.value = null
      }
    }

    // Load existing comments
    try {
      const res = await docsApi.getComments(docId.value)
      comments.value = res.data
    } catch {
      // non-fatal
    }

    // WebSocket handlers
    socket.onInit((data) => {
      editorRef.value?.applyRemote(data.content)
    })

    socket.onEdit((data) => {
      editorRef.value?.applyRemote(data.delta)
    })

    socket.onCursor((data) => {
      editorRef.value?.updateCursor({
        user_id: data.user_id,
        username: data.username,
        color: data.color,
        from: data.position.from,
        to: data.position.to,
      })
    })

    socket.onUserLeave((userId) => {
      editorRef.value?.clearCursor(userId)
    })

    socket.onCommentAdd((comment) => {
      if (!comments.value.find(c => c.id === comment.id)) {
        comments.value.push(comment)
        applyCommentHighlights()
        showComments.value = true
      }
    })

    socket.onCommentDelete((commentId) => {
      comments.value = comments.value.filter(c => c.id !== commentId)
      applyCommentHighlights()
    })

    socket.onCommentUpdate((comment) => {
      const idx = comments.value.findIndex(c => c.id === comment.id)
      if (idx !== -1) {
        comments.value[idx] = comment
        applyCommentHighlights()
      }
    })

    socket.onFullReplace((data) => {
      editorRef.value?.applyRemote(data.content)
      if (doc.value) doc.value.content = JSON.stringify(data.content)
    })

    socket.onPageLayout((layout) => {
      pageLayout.value = {
        page_width: layout.page_width ?? pageLayout.value.page_width,
        page_height: layout.page_height ?? pageLayout.value.page_height,
        margin_top: layout.margin_top ?? pageLayout.value.margin_top,
        margin_right: layout.margin_right ?? pageLayout.value.margin_right,
        margin_bottom: layout.margin_bottom ?? pageLayout.value.margin_bottom,
        margin_left: layout.margin_left ?? pageLayout.value.margin_left,
      }
      // Header / footer / numbering are also delivered here.
      const layoutAny = layout as unknown as Record<string, unknown>
      if ('header_content' in layoutAny && typeof layoutAny.header_content === 'string') {
        headerContent.value = layoutAny.header_content
        editorRef.value?.applyRemoteHeader(parseMaybeJson(layoutAny.header_content))
      }
      if ('footer_content' in layoutAny && typeof layoutAny.footer_content === 'string') {
        footerContent.value = layoutAny.footer_content
        editorRef.value?.applyRemoteFooter(parseMaybeJson(layoutAny.footer_content))
      }
      if ('show_page_numbers' in layoutAny) showPageNumbers.value = !!layoutAny.show_page_numbers
      if ('page_number_start' in layoutAny && typeof layoutAny.page_number_start === 'number') {
        pageNumberStart.value = layoutAny.page_number_start
      }
      if (doc.value) Object.assign(doc.value, layoutAny)
    })

    socket.connect()

    if (myRole.value === 'owner') {
      docsStore.fetchAccesses(docId.value)
    }
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 403 || err.response?.status === 404) {
      loadError.value = 'Документ не существует или у вас нет к нему доступа.'
    } else {
      loadError.value = 'Не удалось загрузить документ.'
    }
  } finally {
    isLoading.value = false
  }
})

// Apply highlights after editor mounts (it may be null during onMounted)
watch(editorRef, (ref) => {
  if (ref && comments.value.length) applyCommentHighlights()
})

function onEditorUpdate(content: unknown) {
  if (!canEdit.value) return
  if (contentSaveTimer) clearTimeout(contentSaveTimer)
  contentSaveTimer = setTimeout(() => {
    socket.sendEdit(content, content)
    showSaved()
  }, 600)
}

function onSelectionUpdate(from: number, to: number, text: string) {
  pendingSelection.value = { from, to }
  if (from !== to) pendingQuote.value = text
  if (canEdit.value) socket.sendCursor(from, to)
}

function openAddComment() {
  if (!pendingSelection.value || pendingSelection.value.from === pendingSelection.value.to) return
  commentText.value = ''
  commentError.value = ''
  showAddComment.value = true
}

async function submitComment() {
  if (!commentText.value.trim() || !pendingSelection.value) return
  commentError.value = ''
  isSubmittingComment.value = true
  try {
    const res = await docsApi.createComment(docId.value, {
      quote: pendingQuote.value,
      from_pos: pendingSelection.value.from,
      to_pos: pendingSelection.value.to,
      content: commentText.value.trim(),
    })
    // Add locally first; WS broadcast will also fire but dedup prevents double
    if (!comments.value.find(c => c.id === res.data.id)) {
      comments.value.push(res.data)
    }
    applyCommentHighlights()
    showComments.value = true
    showAddComment.value = false
    commentText.value = ''
  } catch {
    commentError.value = 'Не удалось опубликовать комментарий. Попробуйте ещё раз.'
  } finally {
    isSubmittingComment.value = false
  }
}

async function handleDeleteComment(commentId: number) {
  try {
    await docsApi.deleteComment(docId.value, commentId)
    // WS broadcast will also handle deletion, but we update locally immediately
    comments.value = comments.value.filter(c => c.id !== commentId)
    applyCommentHighlights()
  } catch {
    // ignore
  }
}

function jumpToComment(from: number, to: number) {
  editorRef.value?.jumpTo(from, to)
}

function onCommentPositionsChanged(payload: {
  updated: Array<{ id: number; from: number; to: number; quote: string }>
  deleted: number[]
}) {
  // Update the sidebar immediately so the user sees live feedback.
  for (const u of payload.updated) {
    const c = comments.value.find(c => c.id === u.id)
    if (c) {
      c.quote = u.quote
      c.from_pos = u.from
      c.to_pos = u.to
    }
  }
  for (const id of payload.deleted) {
    comments.value = comments.value.filter(c => c.id !== id)
  }

  // Accumulate changes for the debounced backend sync.
  for (const u of payload.updated) {
    pendingCommentUpdates.set(u.id, u)
  }
  for (const id of payload.deleted) {
    // A deleted comment doesn't need a PATCH — just a DELETE.
    pendingCommentUpdates.delete(id)
    pendingCommentDeletes.add(id)
  }

  if (commentSyncTimer) clearTimeout(commentSyncTimer)
  commentSyncTimer = setTimeout(syncCommentsToBackend, 500)
}

async function syncCommentsToBackend() {
  commentSyncTimer = null
  const updates = [...pendingCommentUpdates.values()]
  const deletes = [...pendingCommentDeletes]
  pendingCommentUpdates.clear()
  pendingCommentDeletes.clear()

  await Promise.allSettled([
    ...updates.map(u =>
      docsApi.updateComment(docId.value, u.id, {
        quote: u.quote,
        from_pos: u.from,
        to_pos: u.to,
      }),
    ),
    ...deletes.map(id => docsApi.deleteComment(docId.value, id)),
  ])
}

async function onDocxImported(payload: { content: unknown }) {
  // The server already persisted the import + broadcast it over WS. We just
  // need to re-fetch document metadata so page layout / header / footer
  // reflect what came out of the DOCX.
  if (contentSaveTimer) clearTimeout(contentSaveTimer)
  isSaving.value = true
  try {
    const fresh = await docsApi.getDocument(docId.value)
    doc.value = fresh.data
    pageLayout.value = {
      page_width: fresh.data.page_width ?? 816,
      page_height: fresh.data.page_height ?? 1056,
      margin_top: fresh.data.margin_top ?? 96,
      margin_right: fresh.data.margin_right ?? 96,
      margin_bottom: fresh.data.margin_bottom ?? 96,
      margin_left: fresh.data.margin_left ?? 96,
    }
    headerContent.value = fresh.data.header_content ?? ''
    footerContent.value = fresh.data.footer_content ?? ''
    showPageNumbers.value = !!fresh.data.show_page_numbers
    pageNumberStart.value = fresh.data.page_number_start ?? 1
    editorContent.value = payload.content
    // Push fresh header/footer JSON into the band editors so their content
    // matches what was just imported (the WS already does this for OTHER
    // clients; we apply it locally too for the importer's own view).
    editorRef.value?.applyRemoteHeader(parseMaybeJson(fresh.data.header_content))
    editorRef.value?.applyRemoteFooter(parseMaybeJson(fresh.data.footer_content))
  } catch (err) {
    console.error('Failed to refresh document after import', err)
  } finally {
    isSaving.value = false
    lastSaved.value = true
    setTimeout(() => { lastSaved.value = false }, 2000)
  }
}

function parseMaybeJson(s: string | null | undefined): unknown {
  if (!s) return null
  try { return JSON.parse(s) } catch { return null }
}

function onUpdatePageLayout(patch: Partial<PageLayout> & {
  header_content?: string
  footer_content?: string
  show_page_numbers?: boolean
  page_number_start?: number
}) {
  // Apply optimistically.
  pageLayout.value = {
    ...pageLayout.value,
    ...(patch.page_width !== undefined ? { page_width: patch.page_width } : {}),
    ...(patch.page_height !== undefined ? { page_height: patch.page_height } : {}),
    ...(patch.margin_top !== undefined ? { margin_top: patch.margin_top } : {}),
    ...(patch.margin_right !== undefined ? { margin_right: patch.margin_right } : {}),
    ...(patch.margin_bottom !== undefined ? { margin_bottom: patch.margin_bottom } : {}),
    ...(patch.margin_left !== undefined ? { margin_left: patch.margin_left } : {}),
  }
  if (patch.show_page_numbers !== undefined) showPageNumbers.value = patch.show_page_numbers
  if (patch.page_number_start !== undefined) pageNumberStart.value = patch.page_number_start

  if (myRole.value !== 'owner') return
  if (pageLayoutTimer) clearTimeout(pageLayoutTimer)
  pageLayoutTimer = setTimeout(async () => {
    try {
      const updated = await docsApi.updateDocument(docId.value, patch)
      if (doc.value) Object.assign(doc.value, updated.data)
    } catch (err) {
      console.error('Failed to save page layout', err)
    }
  }, 400)
}

function onUpdateHeaderContent(json: unknown) {
  if (!canEdit.value) return
  const serialized = JSON.stringify(json)
  if (serialized === headerContent.value) return
  headerContent.value = serialized
  if (headerSaveTimer) clearTimeout(headerSaveTimer)
  headerSaveTimer = setTimeout(async () => {
    try {
      await docsApi.updateDocument(docId.value, { header_content: serialized })
    } catch (err) {
      console.error('Failed to save header', err)
    }
  }, 600)
}

function onUpdateFooterContent(json: unknown) {
  if (!canEdit.value) return
  const serialized = JSON.stringify(json)
  if (serialized === footerContent.value) return
  footerContent.value = serialized
  if (footerSaveTimer) clearTimeout(footerSaveTimer)
  footerSaveTimer = setTimeout(async () => {
    try {
      await docsApi.updateDocument(docId.value, { footer_content: serialized })
    } catch (err) {
      console.error('Failed to save footer', err)
    }
  }, 600)
}

function showSaved() {
  isSaving.value = true
  setTimeout(() => {
    isSaving.value = false
    lastSaved.value = true
    setTimeout(() => { lastSaved.value = false }, 2000)
  }, 300)
}

function saveTitle() {
  if (!doc.value || editableTitle.value === doc.value.title) return
  if (titleSaveTimer) clearTimeout(titleSaveTimer)
  titleSaveTimer = setTimeout(async () => {
    await docsStore.updateDocument(docId.value, { title: editableTitle.value })
    doc.value = docsStore.currentDocument
  }, 800)
}

async function togglePublic() {
  if (!doc.value) return
  await docsStore.updateDocument(docId.value, { is_public: !doc.value.is_public })
  doc.value = docsStore.currentDocument
}

async function askDelete() {
  if (!doc.value) return
  const ok = window.confirm(
    `Удалить документ «${doc.value.title || 'Без названия'}»? Это действие нельзя отменить.`,
  )
  if (!ok) return
  try {
    await docsStore.deleteDocument(doc.value.id)
    // Drop back to the dashboard once the doc no longer exists.
    router.push('/dashboard')
  } catch {
    window.alert('Не удалось удалить документ.')
  }
}

watch(
  () => docsStore.currentDocument,
  (d) => { if (d) doc.value = d },
)
</script>

<style scoped>
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease;
  overflow: hidden;
}
.slide-panel-enter-from,
.slide-panel-leave-to {
  width: 0;
  opacity: 0;
}
.slide-panel-enter-to,
.slide-panel-leave-from {
  width: 20rem;
  opacity: 1;
}
</style>
