import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '../types'
import * as usersApi from '../api/users'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(true)

  const isAuthenticated = computed(() => !!user.value)

  async function fetchMe() {
    try {
      const res = await usersApi.getMe()
      user.value = res.data
    } catch {
      user.value = null
    } finally {
      isLoading.value = false
    }
  }

  async function login(username: string, password: string) {
    await usersApi.login(username, password)
    await fetchMe()
  }

  async function logout() {
    await usersApi.logout()
    user.value = null
  }

  async function updateProfile(data: FormData | Record<string, unknown>) {
    const res = await usersApi.updateMe(data)
    user.value = res.data
    return res.data
  }

  return { user, isLoading, isAuthenticated, fetchMe, login, logout, updateProfile }
})
