<template>
  <aside class="w-80 shrink-0 border-l border-slate-200 bg-white flex flex-col overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 px-4 py-3 border-b border-slate-200 shrink-0">
      <h3 class="font-semibold text-slate-800 text-sm">
        Комментарии
        <span v-if="comments.length" class="ml-1.5 text-xs font-normal text-slate-400">({{ comments.length }})</span>
      </h3>
      <div class="flex items-center gap-1">
        <button
          v-if="isOwner && comments.length"
          class="h-7 px-2 inline-flex items-center gap-1 rounded border border-red-200 bg-white text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
          title="Удалить все комментарии из документа"
          @click="$emit('deleteAll')"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h8m-7 4h6m-5 4h4M5 7h14l-1 14H6L5 7Zm3 0V4h8v3" />
          </svg>
          Все
        </button>
        <button class="text-slate-400 hover:text-slate-600 transition-colors" @click="$emit('close')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!comments.length" class="flex-1 flex flex-col items-center justify-center text-slate-400 gap-2 px-6 text-center">
      <svg class="w-10 h-10 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      <p class="text-sm">Комментариев пока нет.</p>
      <p class="text-xs">Выделите текст, чтобы оставить комментарий.</p>
    </div>

    <!-- Comment list -->
    <div v-else class="flex-1 overflow-y-auto divide-y divide-slate-100">
      <div
        v-for="comment in comments"
        :key="comment.id"
        class="px-4 py-3 hover:bg-slate-50 transition-colors cursor-pointer group"
        @click="$emit('jump', comment.from_pos, comment.to_pos)"
      >
        <!-- Author row -->
        <div class="flex items-center gap-2 mb-1.5">
          <div
            class="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-white text-xs font-bold overflow-hidden"
            :style="{ backgroundColor: comment.author_color }"
          >
            <img
              v-if="comment.author_avatar"
              :src="resolveMediaUrl(comment.author_avatar)!"
              :alt="comment.author_username"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ comment.author_username[0].toUpperCase() }}</span>
          </div>
          <span class="text-xs font-medium text-slate-700 truncate flex-1">{{ comment.author_username }}</span>
          <span class="text-xs text-slate-400 shrink-0">{{ formatDate(comment.dt_created) }}</span>
          <button
            v-if="canDelete(comment)"
            class="w-5 h-5 flex items-center justify-center rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
            title="Удалить комментарий"
            @click.stop="$emit('delete', comment.id)"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>

        <!-- Quote -->
        <p v-if="comment.quote" class="text-xs text-slate-500 bg-slate-100 rounded px-2 py-1 mb-1.5 line-clamp-2 border-l-2" :style="{ borderColor: comment.author_color }">
          "{{ comment.quote }}"
        </p>

        <!-- Content -->
        <p class="text-sm text-slate-700 leading-relaxed">{{ comment.content }}</p>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { Comment } from '../types'
import { resolveMediaUrl } from '../utils/media'

const props = defineProps<{
  comments: Comment[]
  currentUserId: number | null
  isOwner: boolean
}>()

defineEmits<{
  close: []
  jump: [from: number, to: number]
  delete: [commentId: number]
  deleteAll: []
}>()

function canDelete(comment: Comment): boolean {
  return props.isOwner || comment.author_id === props.currentUserId
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'только что'
  if (diffMin < 60) return `${diffMin} мин назад`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} ч назад`
  return d.toLocaleDateString('ru-RU', { month: 'short', day: 'numeric' })
}
</script>
