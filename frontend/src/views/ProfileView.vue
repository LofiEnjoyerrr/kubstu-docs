<template>
  <div class="pt-14 min-h-screen bg-slate-50">
    <div class="max-w-2xl mx-auto px-4 py-8">
      <div class="mb-6">
        <RouterLink to="/dashboard" class="text-sm text-primary-600 hover:text-primary-800 font-medium flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Личный кабинет
        </RouterLink>
        <h1 class="text-2xl font-bold text-slate-800 mt-2">Настройки профиля</h1>
      </div>

      <div class="card p-6 flex flex-col gap-6">
        <!-- Avatar -->
        <div class="flex items-center gap-5">
          <div class="relative">
            <div class="w-20 h-20 rounded-full overflow-hidden bg-slate-100">
              <img
                v-if="previewUrl || auth.user?.avatar"
                :src="previewUrl || resolveMediaUrl(auth.user?.avatar)!"
                alt="Аватар"
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
              title="Сменить аватар"
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
              На сервисе с {{ joinedDate }}
            </p>
          </div>
        </div>

        <div class="divider" />

        <!-- Push notifications -->
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-semibold text-slate-800">Push-уведомления в браузере</p>
            <p class="text-sm text-slate-500 mt-0.5">
              Когда другой пользователь начинает менять ваш документ, вы
              получите уведомление в браузере — даже если вкладка закрыта.
              Повторное уведомление придёт, если пользователь выйдет из
              документа и начнёт редактировать его заново.
            </p>
            <p
              v-if="push.state.value === 'denied'"
              class="text-xs text-amber-600 mt-1"
            >
              Браузер заблокировал уведомления для этого сайта. Включите их
              в настройках сайта в браузере и перезагрузите страницу.
            </p>
            <p
              v-else-if="push.state.value === 'unsupported'"
              class="text-xs text-slate-400 mt-1"
            >
              Этот браузер не поддерживает push-уведомления.
            </p>
            <p v-if="push.error.value" class="text-xs text-red-600 mt-1">
              {{ push.error.value }}
            </p>
          </div>
          <button
            type="button"
            class="btn-primary shrink-0"
            :disabled="!push.supported || push.isBusy.value || push.state.value === 'denied'"
            @click="onTogglePush"
          >
            {{ pushButtonLabel }}
          </button>
        </div>

        <div class="divider" />

        <!-- Document notification settings -->
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="font-semibold text-slate-800">Уведомления для моих документов</p>
            <p class="text-sm text-slate-500 mt-0.5">
              Значение по умолчанию для уведомлений о редактировании документов,
              которые вы создали. Отдельные документы можно включать или
              выключать независимо от этой настройки.
            </p>
            <p v-if="notificationPrefsError" class="text-xs text-red-600 mt-1">
              {{ notificationPrefsError }}
            </p>
          </div>
          <button
            type="button"
            class="shrink-0"
            :class="globalEditNotificationsEnabled ? 'btn-secondary' : 'btn-primary'"
            :disabled="isLoadingNotificationPrefs || isSavingNotificationPrefs"
            @click="toggleGlobalEditNotifications"
          >
            <svg
              v-if="isLoadingNotificationPrefs || isSavingNotificationPrefs"
              class="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            {{ globalEditNotificationsEnabled ? 'Выключить по умолчанию' : 'Включить по умолчанию' }}
          </button>
        </div>

        <div class="divider" />

        <!-- Form -->
        <form @submit.prevent="saveProfile" class="flex flex-col gap-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="form-group">
              <label class="label" for="first-name">Имя</label>
              <input
                id="first-name"
                v-model="form.first_name"
                class="input"
                type="text"
                autocomplete="given-name"
                placeholder="Иван"
              />
            </div>
            <div class="form-group">
              <label class="label" for="last-name">Фамилия</label>
              <input
                id="last-name"
                v-model="form.last_name"
                class="input"
                type="text"
                autocomplete="family-name"
                placeholder="Иванов"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="label" for="username">Имя пользователя</label>
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
            <p class="text-xs text-slate-400 mt-1">Email изменить нельзя.</p>
          </div>

          <p v-if="saveSuccess" class="text-sm text-green-600 bg-green-50 rounded-lg px-3 py-2">
            Профиль успешно обновлён.
          </p>
          <p v-if="saveError" class="error-text bg-red-50 rounded-lg px-3 py-2">{{ saveError }}</p>

          <div class="flex justify-end">
            <button type="submit" class="btn-primary" :disabled="isSaving">
              <svg v-if="isSaving" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              {{ isSaving ? 'Сохранение…' : 'Сохранить изменения' }}
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
import { usePushNotifications } from '../composables/usePushNotifications'
import * as notificationsApi from '../api/notifications'

const auth = useAuthStore()
const avatarInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const pendingAvatar = ref<File | null>(null)
const isSaving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')
const globalEditNotificationsEnabled = ref(true)
const isLoadingNotificationPrefs = ref(false)
const isSavingNotificationPrefs = ref(false)
const notificationPrefsError = ref('')

const form = reactive({ first_name: '', last_name: '', username: '' })
const errors = reactive({ username: '' })

const push = usePushNotifications()

const pushButtonLabel = computed(() => {
  switch (push.state.value) {
    case 'subscribing': return 'Включаем…'
    case 'unsubscribing': return 'Выключаем…'
    case 'enabled': return 'Отключить уведомления'
    case 'denied': return 'Заблокировано'
    case 'unsupported': return 'Не поддерживается'
    default: return 'Включить уведомления'
  }
})

async function onTogglePush() {
  if (push.isEnabled.value) await push.disable()
  else await push.enable()
}

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
  loadNotificationPreferences()
})

function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  pendingAvatar.value = file
  previewUrl.value = URL.createObjectURL(file)
}

async function loadNotificationPreferences() {
  notificationPrefsError.value = ''
  isLoadingNotificationPrefs.value = true
  try {
    const res = await notificationsApi.getNotificationPreferences()
    globalEditNotificationsEnabled.value = res.data.edit_notifications_enabled
  } catch {
    notificationPrefsError.value = 'Не удалось загрузить настройки уведомлений.'
  } finally {
    isLoadingNotificationPrefs.value = false
  }
}

async function toggleGlobalEditNotifications() {
  notificationPrefsError.value = ''
  isSavingNotificationPrefs.value = true
  const nextValue = !globalEditNotificationsEnabled.value
  try {
    const res = await notificationsApi.updateNotificationPreferences(nextValue)
    globalEditNotificationsEnabled.value = res.data.edit_notifications_enabled
  } catch {
    notificationPrefsError.value = 'Не удалось сохранить настройки уведомлений.'
  } finally {
    isSavingNotificationPrefs.value = false
  }
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
    else saveError.value = 'Не удалось сохранить изменения. Попробуйте ещё раз.'
  } finally {
    isSaving.value = false
  }
}
</script>
