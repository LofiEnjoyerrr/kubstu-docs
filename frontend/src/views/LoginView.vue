<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-14 h-14 bg-white/10 rounded-2xl mb-4">
          <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white">KubSTU Docs</h1>
        <p class="text-primary-300 text-sm mt-1">Sign in with your username or email</p>
      </div>

      <!-- Card -->
      <div class="card p-6 shadow-2xl">
        <form @submit.prevent="handleLogin" class="flex flex-col gap-4">
          <div class="form-group">
            <label class="label" for="username">Username or email</label>
            <input
              id="username"
              v-model="form.username"
              class="input"
              :class="{ 'input-error': errors.username }"
              type="text"
              autocomplete="username"
              placeholder="username or you@example.com"
              required
            />
            <p v-if="errors.username" class="error-text">{{ errors.username }}</p>
          </div>

          <div class="form-group">
            <label class="label" for="password">Password</label>
            <div class="relative">
              <input
                id="password"
                v-model="form.password"
                class="input pr-10"
                :class="{ 'input-error': errors.password }"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            </div>
            <p v-if="errors.password" class="error-text">{{ errors.password }}</p>
          </div>

          <p v-if="errors.global" class="error-text text-center bg-red-50 rounded-lg px-3 py-2">
            {{ errors.global }}
          </p>

          <button type="submit" class="btn-primary btn-lg w-full mt-1" :disabled="isLoading">
            <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            {{ isLoading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>

        <div class="mt-4 text-center text-sm text-slate-500">
          <RouterLink to="/forgot-password" class="text-primary-600 hover:text-primary-800 font-medium">
            Forgot password?
          </RouterLink>
        </div>
      </div>

      <p class="text-center text-primary-300 text-sm mt-6">
        Don't have an account?
        <RouterLink to="/register" class="text-white font-medium hover:underline">Sign up</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ username: '', password: '' })
const errors = reactive({ username: '', password: '', global: '' })
const isLoading = ref(false)
const showPassword = ref(false)

async function handleLogin() {
  errors.username = ''
  errors.password = ''
  errors.global = ''
  isLoading.value = true

  try {
    await auth.login(form.username, form.password)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]>; status?: number } }
    const data = err.response?.data
    if (data?.username) errors.username = data.username[0]
    else if (data?.password) errors.password = data.password[0]
    else if (data?.non_field_errors) errors.global = data.non_field_errors[0]
    else if (err.response?.status === 400) errors.global = 'Invalid credentials.'
    else if (err.response?.status === 429) errors.global = 'Too many attempts. Try again later.'
    else errors.global = 'Something went wrong. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>
