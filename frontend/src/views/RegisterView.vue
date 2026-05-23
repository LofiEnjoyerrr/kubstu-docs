<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4 py-10">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-14 h-14 bg-white/10 rounded-2xl mb-4">
          <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">Создать аккаунт</h1>
        <p class="text-primary-300 text-sm mt-1">Присоединяйтесь к KubSTU Docs</p>
      </div>

      <!-- Success state -->
      <div v-if="success" class="card p-6 text-center shadow-2xl">
        <div class="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-7 h-7 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h2 class="font-semibold text-slate-800 text-lg">Проверьте почту</h2>
        <p class="text-slate-500 text-sm mt-2">
          Мы отправили ссылку для подтверждения на <strong>{{ form.email }}</strong>. Перейдите по ней, чтобы активировать аккаунт.
        </p>
        <p class="text-xs text-slate-400 mt-3">Срок действия ссылки — 45 минут.</p>
      </div>

      <!-- Form -->
      <div v-else class="card p-6 shadow-2xl">
        <form @submit.prevent="handleRegister" class="flex flex-col gap-4">
          <!-- Email -->
          <div class="form-group">
            <label class="label" for="email">Email</label>
            <input
              id="email"
              v-model="form.email"
              class="input"
              :class="{ 'input-error': errors.email }"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
              required
              @blur="checkEmail"
            />
            <p v-if="emailStatus === 'taken'" class="error-text">Этот email уже зарегистрирован.</p>
            <p v-else-if="emailStatus === 'available'" class="text-sm text-green-600">Email свободен.</p>
            <p v-if="errors.email" class="error-text">{{ errors.email }}</p>
          </div>

          <!-- Username (optional) -->
          <div class="form-group">
            <label class="label" for="username">
              Имя пользователя
              <span class="text-slate-400 font-normal">(необязательно)</span>
            </label>
            <input
              id="username"
              v-model="form.username"
              class="input"
              :class="{ 'input-error': errors.username || usernameStatus === 'taken' }"
              type="text"
              autocomplete="username"
              placeholder="сгенерируется автоматически"
              @blur="checkUsername"
            />
            <p v-if="usernameStatus === 'taken'" class="error-text">Это имя уже занято.</p>
            <p v-else-if="usernameStatus === 'available'" class="text-sm text-green-600">Имя свободно.</p>
            <p v-if="errors.username" class="error-text">{{ errors.username }}</p>
          </div>

          <!-- Password -->
          <div class="form-group">
            <label class="label" for="password">Пароль</label>
            <div class="relative">
              <input
                id="password"
                v-model="form.password"
                class="input pr-10"
                :class="{ 'input-error': errors.password }"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="минимум 8 символов"
                minlength="8"
                required
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                @click="showPassword = !showPassword"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path v-if="showPassword" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0zM2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            </div>
            <p v-if="errors.password" class="error-text">{{ errors.password }}</p>
          </div>

          <p v-if="errors.global" class="error-text text-center bg-red-50 rounded-lg px-3 py-2">
            {{ errors.global }}
          </p>

          <button
            type="submit"
            class="btn-primary btn-lg w-full mt-1"
            :disabled="isLoading || usernameStatus === 'taken' || emailStatus === 'taken'"
          >
            <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            {{ isLoading ? 'Создание аккаунта…' : 'Создать аккаунт' }}
          </button>
        </form>
      </div>

      <p class="text-center text-primary-300 text-sm mt-6">
        Уже есть аккаунт?
        <RouterLink to="/login" class="text-white font-medium hover:underline">Войти</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import * as usersApi from '../api/users'

const form = reactive({ email: '', username: '', password: '' })
const errors = reactive({ email: '', username: '', password: '', global: '' })
const isLoading = ref(false)
const success = ref(false)
const showPassword = ref(false)
const usernameStatus = ref<'idle' | 'checking' | 'available' | 'taken'>('idle')
const emailStatus = ref<'idle' | 'checking' | 'available' | 'taken'>('idle')

async function checkUsername() {
  if (!form.username.trim()) { usernameStatus.value = 'idle'; return }
  usernameStatus.value = 'checking'
  try {
    await usersApi.checkUsernameAvailable(form.username)
    usernameStatus.value = 'available'
  } catch {
    usernameStatus.value = 'taken'
  }
}

async function checkEmail() {
  if (!form.email.trim()) { emailStatus.value = 'idle'; return }
  emailStatus.value = 'checking'
  try {
    await usersApi.checkEmailAvailable(form.email)
    emailStatus.value = 'available'
  } catch {
    emailStatus.value = 'taken'
  }
}

async function handleRegister() {
  errors.email = ''
  errors.username = ''
  errors.password = ''
  errors.global = ''

  // Fail-fast client-side check so the user gets the same min-length
  // message the backend would return, without a round-trip.
  if (form.password.length < 8) {
    errors.password = 'Пароль должен содержать не менее 8 символов.'
    return
  }

  isLoading.value = true

  try {
    await usersApi.register(form.email, form.password, form.username || undefined)
    success.value = true
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]>; status?: number } }
    const data = err.response?.data
    if (data?.email) errors.email = data.email[0]
    else if (data?.username) errors.username = data.username[0]
    else if (data?.password) errors.password = data.password[0]
    else if (err.response?.status === 429) errors.global = 'Слишком много попыток. Попробуйте позже.'
    else errors.global = 'Что-то пошло не так. Попробуйте ещё раз.'
  } finally {
    isLoading.value = false
  }
}
</script>
