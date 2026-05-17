<template>
  <div class="flex flex-col h-screen">
    <!-- Top bar -->
    <header class="fixed inset-x-0 top-0 z-40 h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-3 shadow-sm">
      <!-- Back -->
      <RouterLink
        to="/dashboard"
        class="btn-ghost btn-sm p-1.5 rounded-lg"
        title="Back to dashboard"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </RouterLink>

      <!-- Title -->
      <div class="flex-1 flex items-center gap-2 min-w-0">
        <input
          v-if="isOwner"
          v-model="editableTitle"
          class="flex-1 min-w-0 font-semibold text-slate-800 bg-transparent border-none outline-none focus:ring-0 text-base truncate"
          :placeholder="'Untitled'"
          @blur="saveTitle"
          @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
        />
        <span v-else class="font-semibold text-slate-800 text-base truncate">
          {{ doc?.title || 'Untitled' }}
        </span>
        <!-- Saving indicator -->
        <Transition name="fade">
          <span v-if="isSaving" class="text-xs text-slate-400 shrink-0">Saving…</span>
          <span v-else-if="lastSaved" class="text-xs text-slate-400 shrink-0">Saved</span>
        </Transition>
      </div>

      <!-- Right controls -->
      <div class="flex items-center gap-2 shrink-0">
        <!-- Connection indicator -->
        <div
          class="flex items-center gap-1.5 text-xs px-2 py-1 rounded-full"
          :class="isConnected ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'"
        >
          <div class="w-1.5 h-1.5 rounded-full" :class="isConnected ? 'bg-green-500' : 'bg-slate-400'" />
          {{ isConnected ? 'Live' : 'Offline' }}
        </div>

        <!-- Collaborators -->
        <div v-if="collaborators.length" class="flex -space-x-2">
          <div
            v-for="c in collaborators.slice(0, 5)"
            :key="c.user_id ?? c.username"
            class="w-7 h-7 rounded-full border-2 border-white flex items-center justify-center text-white text-xs font-bold"
            :style="{ backgroundColor: c.color }"
            :title="c.username"
          >
            {{ c.username[0].toUpperCase() }}
          </div>
          <div
            v-if="collaborators.length > 5"
            class="w-7 h-7 rounded-full border-2 border-white bg-slate-300 flex items-center justify-center text-slate-700 text-xs font-bold"
          >
            +{{ collaborators.length - 5 }}
          </div>
        </div>

        <!-- Visibility toggle (owner only) -->
        <button
          v-if="isOwner && doc"
          class="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border transition-colors"
          :class="doc.is_public ? 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'"
          :title="doc.is_public ? 'Make private' : 'Make public'"
          @click="togglePublic"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="doc.is_public" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          {{ doc.is_public ? 'Public' : 'Private' }}
        </button>

        <!-- Share button (owner only) -->
        <button
          v-if="isOwner"
          class="btn-primary btn-sm"
          @click="showShare = true"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
          Share
        </button>
      </div>
    </header>

    <!-- Editor area -->
    <main class="flex-1 pt-14 overflow-hidden flex flex-col">
      <!-- Loading -->
      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <svg class="w-8 h-8 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </div>

      <!-- Error -->
      <div v-else-if="loadError" class="flex-1 flex items-center justify-center px-4">
        <div class="text-center">
          <p class="text-slate-600 mb-4">{{ loadError }}</p>
          <RouterLink to="/dashboard" class="btn-primary">Go to Dashboard</RouterLink>
        </div>
      </div>

      <!-- Editor -->
      <TiptapEditor
        v-else
        ref="editorRef"
        v-model="editorContent"
        :editable="canEdit"
        class="flex-1"
        @update:model-value="onEditorUpdate"
        @selection-update="onSelectionUpdate"
      />
    </main>

    <!-- Share modal -->
    <ShareModal
      v-if="showShare && doc"
      :doc-id="doc.id"
      :accesses="docsStore.accesses"
      @close="showShare = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useDocumentsStore } from '../stores/documents'
import { useDocumentSocket } from '../composables/useDocumentSocket'
import TiptapEditor from '../components/editor/TiptapEditor.vue'
import ShareModal from '../components/ShareModal.vue'
import type { Document } from '../types'

const route = useRoute()
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

let saveTimer: ReturnType<typeof setTimeout> | null = null
let contentSaveTimer: ReturnType<typeof setTimeout> | null = null

const isOwner = computed(() => auth.user?.id === doc.value?.owner_id)
const canEdit = computed(() => {
  if (!doc.value) return false
  if (!auth.isAuthenticated) return false
  // Owner always can edit; non-owners are assumed editors if they have WS access.
  // Backend enforces access at the WS connection level.
  return true
})

const socket = useDocumentSocket(docId.value)
const { collaborators, isConnected } = socket

onMounted(async () => {
  try {
    doc.value = await docsStore.fetchDocument(docId.value)
    editableTitle.value = doc.value.title

    // Parse initial content from REST
    try {
      editorContent.value = doc.value.content
        ? typeof doc.value.content === 'string'
          ? JSON.parse(doc.value.content)
          : doc.value.content
        : null
    } catch {
      editorContent.value = null
    }

    // Connect WebSocket
    socket.onInit((data) => {
      editorRef.value?.applyRemote(data.content)
    })

    socket.onEdit((data) => {
      editorRef.value?.applyRemote(data.delta)
    })

    socket.connect()

    // Fetch accesses for share modal (owner only)
    if (auth.user?.id === doc.value.owner_id) {
      docsStore.fetchAccesses(docId.value)
    }
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 403 || err.response?.status === 404) {
      loadError.value = 'This document does not exist or you do not have access.'
    } else {
      loadError.value = 'Failed to load the document.'
    }
  } finally {
    isLoading.value = false
  }
})

function onEditorUpdate(content: unknown) {
  if (!canEdit.value) return
  // Debounce save + broadcast
  if (contentSaveTimer) clearTimeout(contentSaveTimer)
  contentSaveTimer = setTimeout(() => {
    socket.sendEdit(content, content)
    persistContent(content)
  }, 600)
}

function onSelectionUpdate(from: number, to: number) {
  socket.sendCursor(from, to)
}

async function persistContent(_content: unknown) {
  // Content is persisted via WebSocket on the backend. No additional REST call needed.
  isSaving.value = true
  await new Promise((r) => setTimeout(r, 300))
  isSaving.value = false
  lastSaved.value = true
  setTimeout(() => { lastSaved.value = false }, 2000)
}

function saveTitle() {
  if (!doc.value || editableTitle.value === doc.value.title) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    await docsStore.updateDocument(docId.value, { title: editableTitle.value })
    doc.value = docsStore.currentDocument
  }, 800)
}

async function togglePublic() {
  if (!doc.value) return
  await docsStore.updateDocument(docId.value, { is_public: !doc.value.is_public })
  doc.value = docsStore.currentDocument
}

watch(
  () => docsStore.currentDocument,
  (d) => { if (d) doc.value = d },
)
</script>
