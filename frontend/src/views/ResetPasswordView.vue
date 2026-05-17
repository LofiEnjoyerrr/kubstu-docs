<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-white">Set new password</h1>
      </div>

      <div class="card p-6 shadow-2xl">
        <!-- Success -->
        <div v-if="success" class="text-center py-2">
          <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 class="font-semibold text-slate-800 mb-2">Password updated!</h2>
          <p class="text-slate-500 text-sm mb-5">You can now sign in with your new password.</p>
          <RouterLink to="/login" class="btn-primary w-full">Go to sign in</RouterLink>
        </div>

        <!-- Form -->
        <form v-else @submit.prevent="handleSubmit" class="flex flex-col gap-4">
          <div class="form-group">
            <label class="label" for="password">New password</label>
            <div class="relative">
              <input
                id="password"
                v-model="password"
                class="input pr-10"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="at least 8 characters"
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
            {{ isLoading ? 'Updating…' : 'Update password' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import * as usersApi from '../api/users'

const route = useRoute()
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const success = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  isLoading.value = true
  const token = route.params.token as string
  try {
    await usersApi.confirmPasswordReset(token, password.value)
    success.value = true
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]>; status?: number } }
    const data = err.response?.data
    if (data?.password) error.value = data.password[0]
    else if (data?.token) error.value = 'This reset link is invalid or has expired.'
    else if (err.response?.status === 404) error.value = 'This reset link is invalid or has expired.'
    else error.value = 'Something went wrong. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>
