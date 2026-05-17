<template>
  <div class="pt-14 min-h-screen bg-slate-50">
    <div class="max-w-6xl mx-auto px-4 py-8">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">My Documents</h1>
          <p class="text-slate-500 text-sm mt-0.5">
            Welcome back, {{ auth.user?.username }}
          </p>
        </div>
        <button class="btn-primary" @click="showNewDoc = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          New document
        </button>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex justify-center items-center py-24">
        <svg class="w-8 h-8 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </div>

      <template v-else>
        <!-- My documents -->
        <section class="mb-10">
          <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
            Created by me ({{ docs.ownerDocuments.length }})
          </h2>
          <div v-if="!docs.ownerDocuments.length" class="card p-10 text-center text-slate-400">
            <svg class="w-10 h-10 mx-auto mb-3 opacity-40" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
            </svg>
            <p class="text-sm">No documents yet. Create your first one!</p>
          </div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <DocumentCard v-for="doc in docs.ownerDocuments" :key="doc.id" :doc="doc" />
          </div>
        </section>

        <!-- Shared with me -->
        <section v-if="docs.openedDocuments.length">
          <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
            Shared with me ({{ docs.openedDocuments.length }})
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <DocumentCard v-for="doc in docs.openedDocuments" :key="doc.id" :doc="doc" />
          </div>
        </section>
      </template>
    </div>

    <!-- New document modal -->
    <Teleport to="body">
      <div v-if="showNewDoc" class="fixed inset-0 z-50 flex items-center justify-center p-4" @mousedown.self="showNewDoc = false">
        <div class="absolute inset-0 bg-black/40" />
        <div class="relative w-full max-w-sm bg-white rounded-2xl shadow-xl p-6">
          <h2 class="font-semibold text-slate-800 mb-4">New document</h2>
          <form @submit.prevent="createDocument">
            <div class="form-group mb-4">
              <label class="label" for="new-title">Title</label>
              <input
                id="new-title"
                v-model="newTitle"
                class="input"
                type="text"
                placeholder="Untitled document"
                autofocus
                required
              />
            </div>
            <p v-if="createError" class="error-text mb-3">{{ createError }}</p>
            <div class="flex gap-2 justify-end">
              <button type="button" class="btn-secondary" @click="showNewDoc = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="isCreating">
                {{ isCreating ? 'Creating…' : 'Create' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useDocumentsStore } from '../stores/documents'
import DocumentCard from '../components/DocumentCard.vue'

const auth = useAuthStore()
const docs = useDocumentsStore()
const router = useRouter()

const isLoading = ref(true)
const showNewDoc = ref(false)
const newTitle = ref('')
const isCreating = ref(false)
const createError = ref('')

onMounted(async () => {
  try {
    await docs.fetchAvailable()
  } finally {
    isLoading.value = false
  }
})

async function createDocument() {
  createError.value = ''
  isCreating.value = true
  try {
    const doc = await docs.createDocument(newTitle.value.trim() || 'Untitled')
    showNewDoc.value = false
    newTitle.value = ''
    router.push(`/documents/${doc.id}`)
  } catch {
    createError.value = 'Failed to create document.'
  } finally {
    isCreating.value = false
  }
}
</script>
