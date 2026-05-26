<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4" @mousedown.self="$emit('close')">
      <div class="absolute inset-0 bg-black/40" />
      <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-xl flex flex-col max-h-[90vh]">
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 class="font-semibold text-slate-800">Поделиться документом</h2>
          <button class="btn-ghost btn-sm rounded-full p-1" @click="$emit('close')">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
          <!-- Search user -->
          <div>
            <label class="label">Добавить пользователей</label>
            <div class="inline-flex mb-2 rounded-xl border border-slate-200 bg-slate-50 p-1">
              <button
                type="button"
                class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
                :class="searchMode === 'global' ? 'bg-white text-primary-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                @click="setSearchMode('global')"
              >
                Глобально
              </button>
              <button
                type="button"
                class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
                :class="searchMode === 'favorites' ? 'bg-white text-primary-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                @click="setSearchMode('favorites')"
              >
                Избранные
              </button>
            </div>
            <div class="relative">
              <input
                v-model="searchQuery"
                class="input pr-10"
                type="text"
                :placeholder="searchPlaceholder"
                @input="onSearch"
                @focus="onSearchFocus"
                @blur="closeSearchSoon"
              />
              <div v-if="isSearching" class="absolute right-3 top-1/2 -translate-y-1/2">
                <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
              </div>

              <!-- Search results -->
              <div
                v-if="showSearchResults"
                class="absolute z-20 mt-2 w-full border border-slate-200 rounded-xl overflow-hidden shadow-lg bg-white"
              >
                <div v-if="isSearching" class="px-3 py-3 text-sm text-slate-500">
                  Поиск...
                </div>

                <template v-else>
                  <div
                    v-for="u in searchResults"
                    :key="u.id"
                    class="flex items-center gap-3 w-full px-3 py-2.5 hover:bg-primary-50 transition-colors text-left cursor-pointer"
                    role="button"
                    tabindex="0"
                    @mousedown.prevent="selectUser(u)"
                    @keydown.enter.prevent="selectUser(u)"
                    @keydown.space.prevent="selectUser(u)"
                  >
                    <div
                      class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 overflow-hidden"
                      :style="{ backgroundColor: u.color }"
                    >
                      <img
                        v-if="resolveMediaUrl(u.avatar)"
                        :src="resolveMediaUrl(u.avatar)!"
                        class="w-8 h-8 rounded-full object-cover"
                        alt=""
                      />
                      <span v-else>{{ u.username[0].toUpperCase() }}</span>
                    </div>
                    <div class="min-w-0 flex-1">
                      <p class="text-sm font-medium text-slate-800 truncate">{{ u.username }}</p>
                      <p class="text-xs text-slate-500 truncate">{{ u.email }}</p>
                    </div>
                    <button
                      type="button"
                      class="btn-ghost btn-sm px-2 py-1 rounded-lg shrink-0"
                      :class="u.is_favorite ? 'text-amber-500 hover:text-amber-600' : 'text-slate-400 hover:text-amber-500'"
                      :disabled="favoriteBusyId === u.id"
                      :title="u.is_favorite ? 'Убрать из избранных' : 'Добавить в избранные'"
                      @mousedown.stop.prevent="toggleFavorite(u)"
                    >
                      <svg class="w-4 h-4" :fill="u.is_favorite ? 'currentColor' : 'none'" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.48 3.5a.6.6 0 011.04 0l2.45 4.97 5.49.8a.6.6 0 01.33 1.02l-3.97 3.87.94 5.46a.6.6 0 01-.87.64L12 17.69l-4.9 2.57a.6.6 0 01-.86-.64l.93-5.46-3.96-3.87a.6.6 0 01.33-1.02l5.49-.8 2.45-4.97z" />
                      </svg>
                    </button>
                  </div>

                  <div v-if="!searchResults.length" class="px-3 py-3 text-sm text-slate-500">
                    {{ searchMode === 'favorites' ? 'В избранных пока ничего не найдено.' : 'Пользователи не найдены.' }}
                  </div>

                  <div
                    v-if="searchMode === 'favorites' && favoriteTotalCount > 0"
                    class="flex items-center justify-between gap-2 px-3 py-2 border-t border-slate-100 bg-slate-50"
                  >
                    <span class="text-xs text-slate-500">
                      Страница {{ favoritePage }} из {{ favoriteTotalPages }}
                    </span>
                    <div class="flex items-center gap-1">
                      <button
                        type="button"
                        class="btn-ghost btn-sm px-2 py-1"
                        :disabled="favoritePage <= 1"
                        @mousedown.stop.prevent="changeFavoritePage(-1)"
                      >
                        Назад
                      </button>
                      <button
                        type="button"
                        class="btn-ghost btn-sm px-2 py-1"
                        :disabled="favoritePage >= favoriteTotalPages"
                        @mousedown.stop.prevent="changeFavoritePage(1)"
                      >
                        Далее
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>

            <!-- Add panel for selected user -->
            <div v-if="selectedUser" class="mt-3 flex items-center gap-3 p-3 bg-primary-50 rounded-xl border border-primary-200">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 overflow-hidden"
                :style="{ backgroundColor: selectedUser.color }"
              >
                <img
                  v-if="resolveMediaUrl(selectedUser.avatar)"
                  :src="resolveMediaUrl(selectedUser.avatar)!"
                  class="w-8 h-8 rounded-full object-cover"
                  alt=""
                />
                <span v-else>{{ selectedUser.username[0].toUpperCase() }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">{{ selectedUser.username }}</p>
              </div>
              <select v-model="newRole" class="input !w-32">
                <option value="viewer">Наблюдатель</option>
                <option value="editor">Редактор</option>
              </select>
              <button class="btn-primary btn-sm" :disabled="isAdding" @click="addAccess">
                {{ isAdding ? 'Добавление…' : 'Добавить' }}
              </button>
              <button class="btn-ghost btn-sm p-1 rounded-full" @click="selectedUser = null">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p v-if="addError" class="error-text mt-2">{{ addError }}</p>
          </div>

          <!-- Divider -->
          <div class="divider" />

          <!-- Existing accesses -->
          <div>
            <h3 class="text-sm font-medium text-slate-700 mb-3">Пользователи с доступом</h3>

            <div v-if="!accesses.length" class="text-sm text-slate-400 text-center py-4">
              Пока никто не имеет доступа.
            </div>

            <ul class="flex flex-col gap-2">
              <li
                v-for="access in accesses"
                :key="access.id"
                class="flex items-center gap-3"
              >
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 overflow-hidden"
                  :style="{ backgroundColor: access.color }"
                >
                  <!-- ``access.avatar`` is a relative ``/media/...`` path coming
                       from the backend. Rendering it raw makes the browser
                       resolve it against the frontend origin (Vite on :5173 or
                       the static host in prod) instead of Django — same as the
                       rest of the app, we route it through ``resolveMediaUrl``
                       so it points at the backend regardless of where the page
                       was served from. -->
                  <img
                    v-if="resolveMediaUrl(access.avatar)"
                    :src="resolveMediaUrl(access.avatar)!"
                    class="w-8 h-8 rounded-full object-cover"
                    alt=""
                  />
                  <span v-else>{{ access.username[0].toUpperCase() }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ access.username }}</p>
                </div>
                <select
                  :value="access.role"
                  class="input !w-32"
                  @change="changeRole(access.id, ($event.target as HTMLSelectElement).value as 'viewer' | 'editor')"
                >
                  <option value="viewer">Наблюдатель</option>
                  <option value="editor">Редактор</option>
                </select>
                <button
                  v-if="access.role === 'editor'"
                  class="btn-ghost btn-sm p-1 rounded-full"
                  :class="access.is_favorite ? 'text-amber-500 hover:text-amber-600' : 'text-slate-400 hover:text-amber-500'"
                  :disabled="favoriteBusyId === access.user_id"
                  :title="access.is_favorite ? 'Убрать из избранных' : 'Добавить редактора в избранные'"
                  @click="toggleAccessFavorite(access)"
                >
                  <svg class="w-4 h-4" :fill="access.is_favorite ? 'currentColor' : 'none'" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.48 3.5a.6.6 0 011.04 0l2.45 4.97 5.49.8a.6.6 0 01.33 1.02l-3.97 3.87.94 5.46a.6.6 0 01-.87.64L12 17.69l-4.9 2.57a.6.6 0 01-.86-.64l.93-5.46-3.96-3.87a.6.6 0 01.33-1.02l5.49-.8 2.45-4.97z" />
                  </svg>
                </button>
                <button
                  class="btn-ghost btn-sm p-1 rounded-full text-red-500 hover:text-red-600 hover:bg-red-50"
                  :title="`Удалить ${access.username}`"
                  @click="removeAccess(access.id)"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { DocumentAccess, User } from '../types'
import { useDocumentsStore } from '../stores/documents'
import { resolveMediaUrl } from '../utils/media'
import * as usersApi from '../api/users'

const props = defineProps<{ docId: number; accesses: DocumentAccess[] }>()
defineEmits<{ close: [] }>()

const docsStore = useDocumentsStore()

type SearchMode = 'global' | 'favorites'

const searchQuery = ref('')
const searchResults = ref<User[]>([])
const isSearching = ref(false)
const searchMode = ref<SearchMode>('global')
const isSearchOpen = ref(false)
const selectedUser = ref<User | null>(null)
const newRole = ref<'viewer' | 'editor'>('editor')
const isAdding = ref(false)
const addError = ref('')
const favoritePage = ref(1)
const favoriteTotalPages = ref(1)
const favoriteTotalCount = ref(0)
const favoriteBusyId = ref<number | null>(null)

const favoritePageSize = 8

const accessedIds = computed(() => new Set(props.accesses.map((a) => a.user_id)))
const searchPlaceholder = computed(() => (
  searchMode.value === 'global'
    ? 'Поиск по логину или почте во всех пользователях...'
    : 'Введите логин или почту либо выберите из списка...'
))
const showSearchResults = computed(() => (
  isSearchOpen.value && (isSearching.value || searchResults.value.length > 0 || searchMode.value === 'favorites')
))

let searchTimer: ReturnType<typeof setTimeout> | null = null

function filterAvailableUsers(users: User[]) {
  return users.filter((u) => !accessedIds.value.has(u.id))
}

function setSearchMode(mode: SearchMode) {
  searchMode.value = mode
  searchQuery.value = ''
  searchResults.value = []
  selectedUser.value = null
  favoritePage.value = 1
  favoriteTotalPages.value = 1
  favoriteTotalCount.value = 0
  isSearchOpen.value = true
  if (mode === 'favorites') void fetchFavoriteUsers(1)
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  isSearchOpen.value = true

  if (searchMode.value === 'global' && !searchQuery.value.trim()) {
    searchResults.value = []
    return
  }

  searchTimer = setTimeout(() => {
    if (searchMode.value === 'global') void doSearch()
    else void fetchFavoriteUsers(1)
  }, 300)
}

function onSearchFocus() {
  isSearchOpen.value = true
  if (searchMode.value === 'favorites' && !searchResults.value.length) {
    void fetchFavoriteUsers(favoritePage.value)
  }
}

function closeSearchSoon() {
  window.setTimeout(() => {
    isSearchOpen.value = false
  }, 120)
}

async function doSearch() {
  isSearching.value = true
  try {
    const res = await usersApi.searchUsers(searchQuery.value.trim())
    searchResults.value = filterAvailableUsers(res.data)
  } catch {
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

async function fetchFavoriteUsers(page: number) {
  isSearching.value = true
  try {
    const res = await usersApi.getFavoriteUsers({
      q: searchQuery.value.trim(),
      page,
      page_size: favoritePageSize,
    })
    favoritePage.value = res.data.page
    favoriteTotalPages.value = res.data.total_pages
    favoriteTotalCount.value = res.data.count
    searchResults.value = filterAvailableUsers(res.data.results)
  } catch {
    favoritePage.value = 1
    favoriteTotalPages.value = 1
    favoriteTotalCount.value = 0
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

function changeFavoritePage(delta: number) {
  const nextPage = Math.min(Math.max(favoritePage.value + delta, 1), favoriteTotalPages.value)
  if (nextPage !== favoritePage.value) void fetchFavoriteUsers(nextPage)
}

function selectUser(u: User) {
  selectedUser.value = u
  searchQuery.value = ''
  searchResults.value = []
  isSearchOpen.value = false
}

function updateAccessFavoriteFlag(userId: number, isFavorite: boolean) {
  const access = props.accesses.find((a) => a.user_id === userId)
  if (access) access.is_favorite = isFavorite
}

async function toggleFavorite(u: User) {
  if (favoriteBusyId.value) return

  favoriteBusyId.value = u.id
  try {
    if (u.is_favorite) {
      await usersApi.removeFavoriteUser(u.id)
      u.is_favorite = false
      updateAccessFavoriteFlag(u.id, false)
      if (searchMode.value === 'favorites') await fetchFavoriteUsers(favoritePage.value)
    } else {
      const res = await usersApi.addFavoriteUser(u.id)
      u.is_favorite = res.data.is_favorite ?? true
      updateAccessFavoriteFlag(u.id, true)
    }
  } finally {
    favoriteBusyId.value = null
  }
}

async function toggleAccessFavorite(access: DocumentAccess) {
  if (favoriteBusyId.value) return

  favoriteBusyId.value = access.user_id
  try {
    if (access.is_favorite) {
      await usersApi.removeFavoriteUser(access.user_id)
      access.is_favorite = false
      const foundUser = searchResults.value.find((u) => u.id === access.user_id)
      if (foundUser) foundUser.is_favorite = false
    } else {
      await usersApi.addFavoriteUser(access.user_id)
      access.is_favorite = true
      const foundUser = searchResults.value.find((u) => u.id === access.user_id)
      if (foundUser) foundUser.is_favorite = true
    }
  } finally {
    favoriteBusyId.value = null
  }
}

async function addAccess() {
  if (!selectedUser.value) return
  isAdding.value = true
  addError.value = ''
  try {
    await docsStore.addAccess(props.docId, selectedUser.value.id, newRole.value)
    selectedUser.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]> } }
    const detail = Object.values(err.response?.data ?? {}).flat().join(' ')
    addError.value = detail || 'Не удалось предоставить доступ.'
  } finally {
    isAdding.value = false
  }
}

async function changeRole(accessId: number, role: 'viewer' | 'editor') {
  await docsStore.updateAccess(props.docId, accessId, role)
}

async function removeAccess(accessId: number) {
  await docsStore.removeAccess(props.docId, accessId)
}

onMounted(() => docsStore.fetchAccesses(props.docId))
</script>
