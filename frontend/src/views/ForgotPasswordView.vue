<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-white">Forgot password?</h1>
        <p class="text-primary-300 text-sm mt-1">We'll send you a reset link</p>
      </div>

      <div class="card p-6 shadow-2xl">
        <!-- Success -->
        <div v-if="success" class="text-center py-2">
          <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 class="font-semibold text-slate-800 mb-2">Check your email</h2>
          <p class="text-slate-500 text-sm">If that email exists, we sent a reset link. It expires in 30 minutes.</p>
        </div>

        <!-- Form -->
        <form v-else @submit.prevent="handleSubmit" class="flex flex-col gap-4">
          <div class="form-group">
            <label class="label" for="email">Email address</label>
            <input
              id="email"
              v-model="email"
              class="input"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
              required
            />
          </div>

          <p v-if="error" class="error-text text-center bg-red-50 rounded-lg px-3 py-2">{{ error }}</p>

          <button type="submit" class="btn-primary btn-lg w-full" :disabled="isLoading">
            <svg v-if="isLoading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            {{ isLoading ? 'Sending…' : 'Send reset link' }}
          </button>
        </form>
      </div>

      <p class="text-center text-primary-300 text-sm mt-6">
        <RouterLink to="/login" class="text-white font-medium hover:underline">← Back to sign in</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import * as usersApi from '../api/users'

const email = ref('')
const isLoading = ref(false)
const success = ref(false)
const error = ref('')

async function handleSubmit() {
  error.value = ''
  isLoading.value = true
  try {
    await usersApi.requestPasswordReset(email.value)
    success.value = true
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 429) error.value = 'Too many attempts. Try again later.'
    else success.value = true // don't reveal if email exists
  } finally {
    isLoading.value = false
  }
}
</script>
