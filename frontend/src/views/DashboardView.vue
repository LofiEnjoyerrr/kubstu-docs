<template>
  <div class="pt-14 min-h-screen bg-slate-50">
    <div class="max-w-6xl mx-auto px-4 py-8">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-bold text-slate-800">Мои документы</h1>
          <p class="text-slate-500 text-sm mt-0.5">
            С возвращением, {{ auth.user?.username }}
          </p>
        </div>
        <button class="btn-primary" @click="showNewDoc = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Новый документ
        </button>
      </div>

      <!-- Search bar -->
      <div class="mb-8">
        <div class="relative max-w-xl">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Поиск публичных документов…"
            class="input pl-9 w-full"
            @input="onSearchInput"
          />
          <div v-if="isSearching" class="absolute right-3 top-1/2 -translate-y-1/2">
            <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Search results -->
      <template v-if="searchQuery.trim()">
        <section class="mb-10">
          <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
            Результаты поиска{{ searchResults.length ? ` (${searchResults.length})` : '' }}
          </h2>
          <div v-if="!isSearching && !searchResults.length" class="card p-10 text-center text-slate-400">
            <svg class="w-10 h-10 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm">Публичные документы по запросу «{{ searchQuery }}» не найдены</p>
          </div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <DocumentCard v-for="doc in searchResults" :key="doc.id" :doc="doc" />
          </div>
        </section>
      </template>

      <!-- My documents -->
      <template v-else>
        <!-- Loading -->
        <div v-if="isLoading" class="flex justify-center items-center py-24">
          <svg class="w-8 h-8 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        </div>

        <template v-else>
          <section class="mb-10">
            <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
              Созданные мной ({{ docs.ownerDocuments.length }})
            </h2>
            <div v-if="!docs.ownerDocuments.length" class="card p-10 text-center text-slate-400">
              <svg class="w-10 h-10 mx-auto mb-3 opacity-40" fill="currentColor" viewBox="0 0 24 24">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
              </svg>
              <p class="text-sm">Документов пока нет. Создайте первый!</p>
            </div>
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              <DocumentCard v-for="doc in docs.ownerDocuments" :key="doc.id" :doc="doc" />
            </div>
          </section>

          <section v-if="docs.openedDocuments.length">
            <div class="flex flex-col gap-3 mb-4">
              <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                Доступные мне ({{ openedDocumentsCountLabel }})
              </h2>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
                <input
                  v-model="openedAuthorFilter"
                  type="search"
                  class="input"
                  placeholder="Автор"
                  aria-label="Фильтр по автору"
                />
                <input
                  v-model="openedTitleFilter"
                  type="search"
                  class="input"
                  placeholder="Название"
                  aria-label="Фильтр по названию"
                />
                <label class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-slate-500">Дата создания с</span>
                  <input
                    v-model="openedCreatedFrom"
                    type="date"
                    class="input"
                    aria-label="Дата создания от"
                  />
                </label>
                <label class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-slate-500">Дата создания по</span>
                  <input
                    v-model="openedCreatedTo"
                    type="date"
                    class="input"
                    aria-label="Дата создания до"
                  />
                </label>
                <button
                  type="button"
                  class="btn-secondary"
                  :disabled="!hasOpenedFilters"
                  @click="clearOpenedFilters"
                >
                  Сбросить
                </button>
              </div>
            </div>
            <div v-if="!filteredOpenedDocuments.length" class="card p-10 text-center text-slate-400">
              <p class="text-sm">Документы по заданным фильтрам не найдены</p>
            </div>
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              <DocumentCard v-for="doc in filteredOpenedDocuments" :key="doc.id" :doc="doc" />
            </div>
          </section>
        </template>
      </template>
    </div>

    <!-- New document modal -->
    <Teleport to="body">
      <div v-if="showNewDoc" class="fixed inset-0 z-50 flex items-center justify-center p-4" @mousedown.self="showNewDoc = false">
        <div class="absolute inset-0 bg-black/40" />
        <div class="relative w-full max-w-sm bg-white rounded-2xl shadow-xl p-6">
          <h2 class="font-semibold text-slate-800 mb-4">Новый документ</h2>
          <form @submit.prevent="createDocument">
            <div class="form-group mb-4">
              <label class="label" for="new-title">Заголовок</label>
              <input
                id="new-title"
                v-model="newTitle"
                class="input"
                type="text"
                placeholder="Документ без названия"
                autofocus
                required
              />
            </div>
            <p v-if="createError" class="error-text mb-3">{{ createError }}</p>
            <div class="flex gap-2 justify-end">
              <button type="button" class="btn-secondary" @click="showNewDoc = false">Отмена</button>
              <button type="submit" class="btn-primary" :disabled="isCreating">
                {{ isCreating ? 'Создание…' : 'Создать' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useDocumentsStore } from '../stores/documents'
import DocumentCard from '../components/DocumentCard.vue'
import * as docsApi from '../api/documents'
import type { Document } from '../types'

const auth = useAuthStore()
const docs = useDocumentsStore()
const router = useRouter()

const isLoading = ref(true)
const showNewDoc = ref(false)
const newTitle = ref('')
const isCreating = ref(false)
const createError = ref('')

const searchQuery = ref('')
const searchResults = ref<Document[]>([])
const isSearching = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const openedAuthorFilter = ref('')
const openedTitleFilter = ref('')
const openedCreatedFrom = ref('')
const openedCreatedTo = ref('')

const hasOpenedFilters = computed(() =>
  Boolean(
    openedAuthorFilter.value.trim()
    || openedTitleFilter.value.trim()
    || openedCreatedFrom.value
    || openedCreatedTo.value,
  ),
)

const filteredOpenedDocuments = computed(() => {
  const author = normalizeFilter(openedAuthorFilter.value)
  const title = normalizeFilter(openedTitleFilter.value)
  const createdFrom = parseDateStart(openedCreatedFrom.value)
  const createdTo = parseDateEnd(openedCreatedTo.value)

  return docs.openedDocuments.filter((doc) => {
    const createdAt = new Date(doc.dt_created).getTime()

    return (
      (!author || normalizeFilter(doc.owner).includes(author))
      && (!title || normalizeFilter(doc.title).includes(title))
      && (createdFrom === null || createdAt >= createdFrom)
      && (createdTo === null || createdAt <= createdTo)
    )
  })
})

const openedDocumentsCountLabel = computed(() => {
  if (!hasOpenedFilters.value) return String(docs.openedDocuments.length)
  return `${filteredOpenedDocuments.value.length} из ${docs.openedDocuments.length}`
})

onMounted(async () => {
  try {
    await docs.fetchAvailable()
  } finally {
    isLoading.value = false
  }
})

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    return
  }
  isSearching.value = true
  searchTimer = setTimeout(async () => {
    try {
      const res = await docsApi.searchDocuments(q)
      searchResults.value = res.data
    } catch {
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 400)
}

function normalizeFilter(value: string) {
  return value.trim().toLocaleLowerCase('ru-RU')
}

function parseDateStart(value: string) {
  if (!value) return null
  return new Date(`${value}T00:00:00`).getTime()
}

function parseDateEnd(value: string) {
  if (!value) return null
  return new Date(`${value}T23:59:59.999`).getTime()
}

function clearOpenedFilters() {
  openedAuthorFilter.value = ''
  openedTitleFilter.value = ''
  openedCreatedFrom.value = ''
  openedCreatedTo.value = ''
}

async function createDocument() {
  createError.value = ''
  isCreating.value = true
  try {
    const doc = await docs.createDocument(newTitle.value.trim() || 'Без названия')
    showNewDoc.value = false
    newTitle.value = ''
    router.push(`/documents/${doc.id}`)
  } catch {
    createError.value = 'Не удалось создать документ.'
  } finally {
    isCreating.value = false
  }
}
</script>
