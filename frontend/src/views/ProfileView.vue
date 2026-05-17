<template>
  <div class="pt-14 min-h-screen bg-slate-50">
    <div class="max-w-2xl mx-auto px-4 py-8">
      <div class="mb-6">
        <RouterLink to="/dashboard" class="text-sm text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Dashboard
        </RouterLink>
        <h1 class="text-2xl font-bold text-slate-800 mt-2">Profile settings</h1>
      </div>

      <div class="card p-6 flex flex-col gap-6">
        <!-- Avatar -->
        <div class="flex items-center gap-5">
          <div class="relative">
            <div class="w-20 h-20 rounded-full overflow-hidden bg-slate-100">
              <img
                v-if="previewUrl || auth.user?.avatar"
                :src="previewUrl || resolveMediaUrl(auth.user?.avatar)!"
                alt="Avatar"
                class="w-full h-full object-cover"
              />
              <div
                v-else
                class="w-full h-full flex items-center justify-center text-2xl font-bold text-white"
                :style="{ backgroundColor: auth.user?.color }"
              >
                {{ initials }}
              </div>
            </div>
            <button
              class="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-primary-600 text-white flex items-center justify-center hover:bg-primary-700 transition-colors shadow-md"
              title="Change avatar"
              @click="avatarInput?.click()"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
            <input
              ref="avatarInput"
              type="file"
              class="hidden"
              accept="image/*"
              @change="onAvatarChange"
            />
          </div>
          <div>
            <p class="font-semibold text-slate-800">{{ auth.user?.username }}</p>
            <p class="text-sm text-slate-500">{{ auth.user?.email }}</p>
            <p class="text-xs text-slate-400 mt-0.5">
              Member since {{ joinedDate }}
            </p>
          </div>
        </div>

        <div class="divider" />

        <!-- Form -->
        <form @submit.prevent="saveProfile" class="flex flex-col gap-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="form-group">
              <label class="label" for="first-name">First name</label>
              <input
                id="first-name"
                v-model="form.first_name"
                class="input"
                type="text"
                autocomplete="given-name"
                placeholder="John"
              />
            </div>
            <div class="form-group">
              <label class="label" for="last-name">Last name</label>
              <input
                id="last-name"
                v-model="form.last_name"
                class="input"
                type="text"
                autocomplete="family-name"
                placeholder="Doe"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="label" for="username">Username</label>
            <input
              id="username"
              v-model="form.username"
              class="input"
              :class="{ 'input-error': errors.username }"
              type="text"
              autocomplete="username"
            />
            <p v-if="errors.username" class="error-text">{{ errors.username }}</p>
          </div>

          <div class="form-group">
            <label class="label">Email</label>
            <input :value="auth.user?.email" class="input bg-slate-50" type="email" disabled />
            <p class="text-xs text-slate-400 mt-1">Email cannot be changed.</p>
          </div>

          <p v-if="saveSuccess" class="text-sm text-green-600 bg-green-50 rounded-lg px-3 py-2">
            Profile updated successfully.
          </p>
          <p v-if="saveError" class="error-text bg-red-50 rounded-lg px-3 py-2">{{ saveError }}</p>

          <div class="flex justify-end">
            <button type="submit" class="btn-primary" :disabled="isSaving">
              <svg v-if="isSaving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              {{ isSaving ? 'Saving…' : 'Save changes' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { resolveMediaUrl } from '../utils/media'

const auth = useAuthStore()
const avatarInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const pendingAvatar = ref<File | null>(null)
const isSaving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

const form = reactive({ first_name: '', last_name: '', username: '' })
const errors = reactive({ username: '' })

const initials = computed(() => {
  const u = auth.user
  if (!u) return ''
  if (u.first_name || u.last_name)
    return `${u.first_name?.[0] ?? ''}${u.last_name?.[0] ?? ''}`.toUpperCase()
  return u.username[0].toUpperCase()
})

const joinedDate = computed(() => {
  if (!auth.user?.date_joined) return ''
  return new Date(auth.user.date_joined).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
})

onMounted(() => {
  if (auth.user) {
    form.first_name = auth.user.first_name
    form.last_name = auth.user.last_name
    form.username = auth.user.username
  }
})

function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  pendingAvatar.value = file
  previewUrl.value = URL.createObjectURL(file)
}

async function saveProfile() {
  errors.username = ''
  saveError.value = ''
  saveSuccess.value = false
  isSaving.value = true

  try {
    if (pendingAvatar.value) {
      const fd = new FormData()
      fd.append('first_name', form.first_name)
      fd.append('last_name', form.last_name)
      fd.append('username', form.username)
      fd.append('avatar', pendingAvatar.value)
      await auth.updateProfile(fd)
      pendingAvatar.value = null
    } else {
      await auth.updateProfile({
        first_name: form.first_name,
        last_name: form.last_name,
        username: form.username,
      })
    }
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: Record<string, string[]> } }
    const data = err.response?.data
    if (data?.username) errors.username = data.username[0]
    else saveError.value = 'Failed to save changes. Please try again.'
  } finally {
    isSaving.value = false
  }
}
</script>
