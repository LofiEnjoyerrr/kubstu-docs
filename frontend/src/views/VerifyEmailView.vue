<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="w-full max-w-md">

      <!-- Verifying -->
      <Transition name="fade" mode="out-in">
        <div v-if="state === 'loading'" key="loading" class="card p-10 text-center shadow-2xl">
          <div class="relative w-16 h-16 mx-auto mb-6">
            <svg class="w-16 h-16 animate-spin text-primary-200" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"/>
              <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2zm0 4.236l-8 4.882-8-4.882V6h16v2.236z"/>
              </svg>
            </div>
          </div>
          <h2 class="text-xl font-semibold text-slate-800 mb-2">Подтверждение email…</h2>
          <p class="text-slate-500 text-sm">Подождите немного.</p>
        </div>

        <!-- Success -->
        <div v-else-if="state === 'success'" key="success" class="card p-10 text-center shadow-2xl">
          <!-- Animated checkmark -->
          <div class="relative w-20 h-20 mx-auto mb-6">
            <svg class="w-20 h-20" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="38" fill="none" stroke="#dbeafe" stroke-width="4"/>
              <circle
                cx="40" cy="40" r="38"
                fill="none"
                stroke="#2563eb"
                stroke-width="4"
                stroke-linecap="round"
                stroke-dasharray="239"
                :stroke-dashoffset="progressOffset"
                transform="rotate(-90 40 40)"
                style="transition: stroke-dashoffset 1s linear;"
              />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
              <div class="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                <svg class="w-7 h-7 text-primary-600 checkmark" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
            </div>
          </div>

          <h2 class="text-2xl font-bold text-slate-800 mb-2">Email подтверждён!</h2>
          <p class="text-slate-500 text-sm mb-1">Ваш аккаунт активирован.</p>
          <p class="text-slate-400 text-xs mb-8">
            Вход выполнен как <span class="font-medium text-primary-600">{{ auth.user?.username }}</span>
          </p>

          <!-- Countdown ring -->
          <div class="flex flex-col items-center gap-4">
            <p class="text-sm text-slate-500">
              Перенаправление в личный кабинет через
              <span class="font-semibold text-primary-600 tabular-nums">{{ countdown }} с</span>…
            </p>
            <RouterLink to="/dashboard" class="btn-primary btn-lg w-full">
              Перейти в личный кабинет
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
              </svg>
            </RouterLink>
          </div>
        </div>

        <!-- Error -->
        <div v-else key="error" class="card p-10 text-center shadow-2xl">
          <div class="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg class="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
          </div>
          <h2 class="text-2xl font-bold text-slate-800 mb-2">Подтверждение не удалось</h2>
          <p class="text-slate-500 text-sm mb-8">{{ errorMessage }}</p>
          <div class="flex flex-col gap-3">
            <RouterLink to="/register" class="btn-primary w-full">Зарегистрироваться заново</RouterLink>
            <RouterLink to="/login" class="btn-secondary w-full">Войти</RouterLink>
          </div>
        </div>
      </Transition>

      <!-- Logo below card -->
      <p class="text-center text-primary-400 text-sm mt-6 flex items-center justify-center gap-2">
        <svg class="w-4 h-4 text-primary-300" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
        </svg>
        KubSTU Docs
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import * as usersApi from '../api/users'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const state = ref<'loading' | 'success' | 'error'>('loading')
const errorMessage = ref('Эта ссылка недействительна или уже использована.')
const countdown = ref(5)

// Progress ring: circumference = 2π × 38 ≈ 239
const CIRCUMFERENCE = 239
const progressOffset = computed(() =>
  CIRCUMFERENCE - (CIRCUMFERENCE * (5 - countdown.value)) / 5,
)

let countdownTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  const token = route.params.token as string
  try {
    await usersApi.verifyEmail(token)
    await auth.fetchMe()
    state.value = 'success'

    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(countdownTimer!)
        router.push('/dashboard')
      }
    }, 1000)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    const status = err.response?.status
    if (status === 400 || status === 404) {
      errorMessage.value = 'Эта ссылка подтверждения недействительна или уже использована.'
    } else if (status === 410) {
      errorMessage.value = 'Срок действия ссылки подтверждения истёк. Пожалуйста, зарегистрируйтесь заново.'
    }
    state.value = 'error'
  }
})

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.checkmark {
  stroke-dasharray: 40;
  stroke-dashoffset: 40;
  animation: draw-check 0.4s ease 0.2s forwards;
}
@keyframes draw-check {
  to { stroke-dashoffset: 0; }
}
</style>
