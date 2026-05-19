<template>
  <header class="fixed inset-x-0 top-0 z-40 h-14 bg-primary-900 shadow-lg flex items-center px-4 gap-4">
    <!-- Logo -->
    <RouterLink to="/dashboard" class="flex items-center gap-2 shrink-0 mr-2">
      <svg class="w-7 h-7 text-primary-300" viewBox="0 0 24 24" fill="currentColor">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
      </svg>
      <span class="text-white font-semibold text-base tracking-tight hidden sm:block">KubSTU Docs</span>
    </RouterLink>

    <div class="flex-1" />

    <!-- User menu -->
    <div v-if="auth.user" class="relative" ref="menuRef">
      <button
        class="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-primary-800 transition-colors"
        @click="menuOpen = !menuOpen"
      >
        <div class="relative w-7 h-7">
          <img
            v-if="auth.user.avatar"
            :src="resolveMediaUrl(auth.user.avatar)!"
            :alt="auth.user.username"
            class="w-7 h-7 rounded-full object-cover"
          />
          <div
            v-else
            class="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold"
            :style="{ backgroundColor: auth.user.color }"
          >
            {{ initials }}
          </div>
        </div>
        <span class="text-white text-sm font-medium hidden sm:block max-w-[100px] truncate">
          {{ auth.user.username }}
        </span>
        <svg class="w-4 h-4 text-primary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <Transition name="slide-up">
        <div
          v-if="menuOpen"
          class="absolute right-0 top-full mt-1 w-48 bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-50"
        >
          <div class="px-3 py-2 border-b border-slate-100">
            <p class="text-sm font-medium text-slate-800 truncate">{{ auth.user.username }}</p>
            <p class="text-xs text-slate-500 truncate">{{ auth.user.email }}</p>
          </div>
          <RouterLink
            to="/profile"
            class="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            @click="menuOpen = false"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Профиль
          </RouterLink>
          <button
            class="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            @click="handleLogout"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Выйти
          </button>
        </div>
      </Transition>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { resolveMediaUrl } from '../utils/media'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const initials = computed(() => {
  const u = auth.user
  if (!u) return ''
  if (u.first_name || u.last_name) {
    return `${u.first_name?.[0] ?? ''}${u.last_name?.[0] ?? ''}`.toUpperCase()
  }
  return u.username[0].toUpperCase()
})

async function handleLogout() {
  menuOpen.value = false
  await auth.logout()
  router.push('/login')
}

function handleClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

