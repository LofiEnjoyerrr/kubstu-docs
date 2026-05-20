<template>
  <RouterLink
    :to="`/documents/${doc.id}`"
    class="card p-4 flex flex-col gap-3 hover:border-primary-300 hover:shadow-md transition-all duration-150 group cursor-pointer relative"
  >
    <!-- Icon + title -->
    <div class="flex items-start gap-3">
      <div class="w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center shrink-0 group-hover:bg-primary-200 transition-colors">
        <svg class="w-5 h-5 text-primary-600" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-semibold text-slate-800 text-sm leading-tight group-hover:text-primary-700 transition-colors truncate">
          {{ doc.title || 'Без названия' }}
        </h3>
        <p class="text-xs text-slate-500 mt-0.5">автор: {{ doc.owner }}</p>
      </div>

      <!-- Delete button — only the owner sees it. Stops the RouterLink
           click from firing so deleting doesn't also navigate. -->
      <button
        v-if="canDelete"
        class="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50"
        title="Удалить документ"
        @click.stop.prevent="askDelete"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>

    <!-- Meta -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <span v-if="doc.is_public" class="badge-blue">Публичный</span>
        <span v-else class="badge-slate">Приватный</span>
      </div>
      <time class="text-xs text-slate-400">{{ relativeTime }}</time>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Document } from '../types'
import { useAuthStore } from '../stores/auth'
import { useDocumentsStore } from '../stores/documents'

const props = defineProps<{ doc: Document }>()

const auth = useAuthStore()
const docsStore = useDocumentsStore()

const canDelete = computed(() => auth.user?.id === props.doc.owner_id)

async function askDelete() {
  const ok = window.confirm(`Удалить документ «${props.doc.title || 'Без названия'}»? Это действие нельзя отменить.`)
  if (!ok) return
  try {
    await docsStore.deleteDocument(props.doc.id)
  } catch {
    window.alert('Не удалось удалить документ.')
  }
}

const relativeTime = computed(() => {
  const d = new Date(props.doc.dt_updated)
  const diff = Date.now() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин назад`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ч назад`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} дн назад`
  return d.toLocaleDateString('ru-RU')
})
</script>
