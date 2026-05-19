<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="w-full max-w-md">

      <Transition name="fade" mode="out-in">
        <!-- Success -->
        <div v-if="state === 'success'" key="success" class="card p-10 text-center shadow-2xl">
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

          <h2 class="text-2xl font-bold text-slate-800 mb-2">Пароль обновлён!</h2>
          <p class="text-slate-500 text-sm mb-8">Теперь вы можете войти с новым паролем.</p>

          <div class="flex flex-col items-center gap-4">
            <p class="text-sm text-slate-500">
              Перенаправление на страницу входа через
              <span class="font-semibold text-primary-600 tabular-nums">{{ countdown }} с</span>…
            </p>
            <RouterLink to="/login" class="btn-primary btn-lg w-full">
              Перейти ко входу
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
              </svg>
            </RouterLink>
          </div>
        </div>

        <!-- Form -->
        <div v-else key="form" class="card p-8 shadow-2xl">
          <div class="text-center mb-6">
            <div class="w-14 h-14 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg class="w-7 h-7 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
              </svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-800">Новый пароль</h1>
            <p class="text-slate-500 text-sm mt-1">Выберите надёжный пароль для вашего аккаунта.</p>
          </div>

          <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
            <div class="form-group">
              <label class="label" for="password">Новый пароль</label>
              <div class="relative">
                <input
                  id="password"
                  v-model="password"
                  class="input pr-10"
                  :type="showPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="минимум 8 символов"
                  required
                  minlength="8"
                />
                <button
                  type="button"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  @click="showPassword = !showPassword"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
              </div>
            </div>

            <p v-if="error" class="error-text text-center bg-red-50 rounded-lg px-3 py-2">{{ error }}</p>

            <button type="submit" class="btn-primary btn-lg w-full" :disabled="isLoading">
              <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              {{ isLoading ? 'Обновление…' : 'Обновить пароль' }}
            </button>
          </form>
        </div>
      </Transition>

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
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as usersApi from '../api/users'

const route = useRoute()
const router = useRouter()

const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const state = ref<'form' | 'success'>('form')
const error = ref('')
const countdown = ref(5)

const CIRCUMFERENCE = 239
const progressOffset = computed(() =>
  CIRCUMFERENCE - (CIRCUMFERENCE * (5 - countdown.value)) / 5,
)

let countdownTimer: ReturnType<typeof setInterval> | null = null

async function handleSubmit() {
  error.value = ''
  isLoading.value = true
  const token = route.params.token as string
  try {
    await usersApi.confirmPasswordReset(token, password.value)
    state.value = 'success'
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(countdownTimer!)
        router.push('/login')
      }
    }, 1000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]>; status?: number } }
    const data = err.response?.data
    if (data?.password) error.value = data.password[0]
    else if (data?.token) error.value = 'Эта ссылка для сброса недействительна или истекла.'
    else if (err.response?.status === 404) error.value = 'Эта ссылка для сброса недействительна или истекла.'
    else error.value = 'Что-то пошло не так. Попробуйте ещё раз.'
  } finally {
    isLoading.value = false
  }
}

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
