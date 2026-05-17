<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="card p-8 w-full max-w-sm text-center shadow-2xl">
      <!-- Loading -->
      <template v-if="state === 'loading'">
        <svg class="w-12 h-12 animate-spin text-primary-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
        <h2 class="font-semibold text-slate-700">Verifying your email…</h2>
      </template>

      <!-- Success -->
      <template v-else-if="state === 'success'">
        <div class="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-7 h-7 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 class="font-semibold text-slate-800 text-xl mb-2">Email verified!</h2>
        <p class="text-slate-500 text-sm mb-6">Your account is ready. Redirecting to dashboard…</p>
        <RouterLink to="/dashboard" class="btn-primary w-full">Go to Dashboard</RouterLink>
      </template>

      <!-- Error -->
      <template v-else>
        <div class="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 class="font-semibold text-slate-800 text-xl mb-2">Verification failed</h2>
        <p class="text-slate-500 text-sm mb-6">{{ errorMessage }}</p>
        <RouterLink to="/register" class="btn-primary w-full">Register again</RouterLink>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import * as usersApi from '../api/users'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const state = ref<'loading' | 'success' | 'error'>('loading')
const errorMessage = ref('The link is invalid or has expired.')

onMounted(async () => {
  const token = route.params.token as string
  try {
    await usersApi.verifyEmail(token)
    await auth.fetchMe()
    state.value = 'success'
    setTimeout(() => router.push('/dashboard'), 2000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]>; status?: number } }
    if (err.response?.status === 404 || err.response?.status === 400) {
      errorMessage.value = 'This verification link is invalid or has already been used.'
    } else if (err.response?.status === 410) {
      errorMessage.value = 'This verification link has expired. Please register again.'
    }
    state.value = 'error'
  }
})
</script>
