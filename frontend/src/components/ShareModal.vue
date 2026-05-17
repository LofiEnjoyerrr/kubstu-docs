<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4" @mousedown.self="$emit('close')">
      <div class="absolute inset-0 bg-black/40" />
      <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-xl flex flex-col max-h-[90vh]">
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 class="font-semibold text-slate-800">Share document</h2>
          <button class="btn-ghost btn-sm rounded-full p-1" @click="$emit('close')">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
          <!-- Search user -->
          <div>
            <label class="label">Add people</label>
            <div class="relative">
              <input
                v-model="searchQuery"
                class="input pr-10"
                type="text"
                placeholder="Search by username…"
                @input="onSearch"
              />
              <div v-if="isSearching" class="absolute right-3 top-1/2 -translate-y-1/2">
                <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
              </div>
            </div>

            <!-- Search results -->
            <div v-if="searchResults.length" class="mt-2 border border-slate-200 rounded-xl overflow-hidden shadow-sm">
              <button
                v-for="u in searchResults"
                :key="u.id"
                class="flex items-center gap-3 w-full px-3 py-2.5 hover:bg-primary-50 transition-colors text-left"
                @click="selectUser(u)"
              >
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                  :style="{ backgroundColor: u.color }"
                >
                  {{ u.username[0].toUpperCase() }}
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ u.username }}</p>
                  <p class="text-xs text-slate-500 truncate">{{ u.email }}</p>
                </div>
              </button>
            </div>

            <!-- Add panel for selected user -->
            <div v-if="selectedUser" class="mt-3 flex items-center gap-3 p-3 bg-primary-50 rounded-xl border border-primary-200">
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                :style="{ backgroundColor: selectedUser.color }"
              >
                {{ selectedUser.username[0].toUpperCase() }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">{{ selectedUser.username }}</p>
              </div>
              <select v-model="newRole" class="input !w-28">
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
              </select>
              <button class="btn-primary btn-sm" :disabled="isAdding" @click="addAccess">
                {{ isAdding ? 'Adding…' : 'Add' }}
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
            <h3 class="text-sm font-medium text-slate-700 mb-3">People with access</h3>

            <div v-if="!accesses.length" class="text-sm text-slate-400 text-center py-4">
              No one else has access yet.
            </div>

            <ul class="flex flex-col gap-2">
              <li
                v-for="access in accesses"
                :key="access.id"
                class="flex items-center gap-3"
              >
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                  :style="{ backgroundColor: access.color }"
                >
                  <img v-if="access.avatar" :src="access.avatar" class="w-8 h-8 rounded-full object-cover" />
                  <span v-else>{{ access.username[0].toUpperCase() }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ access.username }}</p>
                </div>
                <select
                  :value="access.role"
                  class="input !w-28"
                  @change="changeRole(access.id, ($event.target as HTMLSelectElement).value as 'viewer' | 'editor')"
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                </select>
                <button
                  class="btn-ghost btn-sm p-1 rounded-full text-red-500 hover:text-red-600 hover:bg-red-50"
                  :title="`Remove ${access.username}`"
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
import { ref, onMounted } from 'vue'
import type { DocumentAccess, User } from '../types'
import { useDocumentsStore } from '../stores/documents'
import * as usersApi from '../api/users'

const props = defineProps<{ docId: number; accesses: DocumentAccess[] }>()
defineEmits<{ close: [] }>()

const docsStore = useDocumentsStore()

const searchQuery = ref('')
const searchResults = ref<User[]>([])
const isSearching = ref(false)
const selectedUser = ref<User | null>(null)
const newRole = ref<'viewer' | 'editor'>('editor')
const isAdding = ref(false)
const addError = ref('')

let searchTimer: ReturnType<typeof setTimeout> | null = null

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) { searchResults.value = []; return }
  searchTimer = setTimeout(doSearch, 300)
}

async function doSearch() {
  isSearching.value = true
  try {
    const res = await usersApi.searchUsers(searchQuery.value.trim())
    const accessedIds = new Set(props.accesses.map((a) => a.user_id))
    searchResults.value = res.data.filter((u) => !accessedIds.has(u.id))
  } catch {
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

function selectUser(u: User) {
  selectedUser.value = u
  searchQuery.value = ''
  searchResults.value = []
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
    addError.value = detail || 'Failed to add access.'
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
