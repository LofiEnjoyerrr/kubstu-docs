import { ref, computed } from 'vue'
import {
  fetchVapidPublicKey,
  subscribePush,
  unsubscribePush,
} from '../api/notifications'

/**
 * Web Push opt-in / opt-out flow.
 *
 * Why this is heavier than a single ``subscribe()`` call:
 *   - browsers need a service worker REGISTRATION before ``pushManager``
 *     exists at all;
 *   - the VAPID public key lives on the backend and has to be fetched
 *     once per session and converted from URL-safe base64 to a
 *     ``Uint8Array`` the PushManager will accept;
 *   - permission can be ``default`` / ``granted`` / ``denied`` and the
 *     UI should reflect each state so the user knows whether clicking
 *     the toggle will actually do anything (a denied permission can
 *     only be reset from the browser's site settings).
 */

export type PushState =
  | 'unsupported'           // browser has no Push API at all
  | 'denied'                // user blocked notifications, opt-in impossible
  | 'idle'                  // permission is "default", no subscription yet
  | 'subscribing'           // in-flight subscribe call
  | 'enabled'               // subscription exists and is registered server-side
  | 'unsubscribing'         // in-flight unsubscribe call

const SERVICE_WORKER_PATH = '/sw.js'

function urlBase64ToUint8Array(b64: string): Uint8Array {
  // The browser's pushManager.subscribe() wants a raw byte array of the
  // P-256 public key. The backend sends URL-safe base64 without padding.
  const padding = '='.repeat((4 - (b64.length % 4)) % 4)
  const normalized = (b64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(normalized)
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

function isSupported(): boolean {
  return (
    typeof window !== 'undefined'
    && 'serviceWorker' in navigator
    && 'PushManager' in window
    && 'Notification' in window
  )
}

let cachedRegistration: ServiceWorkerRegistration | null = null

async function ensureRegistration(): Promise<ServiceWorkerRegistration> {
  if (cachedRegistration) return cachedRegistration
  const reg = await navigator.serviceWorker.register(SERVICE_WORKER_PATH, {
    scope: '/',
  })
  // ``register`` resolves as soon as the install kicks off, but the worker
  // may not be active yet — pushManager calls only succeed against an
  // activated worker, so wait for the ready state.
  await navigator.serviceWorker.ready
  cachedRegistration = reg
  return reg
}

export function usePushNotifications() {
  const state = ref<PushState>('idle')
  const error = ref<string>('')

  const supported = isSupported()
  if (!supported) state.value = 'unsupported'

  const isEnabled = computed(() => state.value === 'enabled')
  const isBusy = computed(() =>
    state.value === 'subscribing' || state.value === 'unsubscribing',
  )

  async function refresh(): Promise<void> {
    if (!supported) return
    if (Notification.permission === 'denied') {
      state.value = 'denied'
      return
    }
    try {
      const reg = await ensureRegistration()
      const sub = await reg.pushManager.getSubscription()
      state.value = sub ? 'enabled' : 'idle'
    } catch (e) {
      console.error('[push] refresh failed', e)
      state.value = 'idle'
    }
  }

  async function enable(): Promise<void> {
    if (!supported || isBusy.value) return
    error.value = ''
    state.value = 'subscribing'
    try {
      // ``requestPermission`` MUST be called from a user gesture handler —
      // this composable's caller (the toggle's click handler) provides it.
      const perm = await Notification.requestPermission()
      if (perm !== 'granted') {
        state.value = perm === 'denied' ? 'denied' : 'idle'
        return
      }

      const reg = await ensureRegistration()
      const publicKey = await fetchVapidPublicKey()
      if (!publicKey) {
        error.value = 'Сервер не настроен для отправки push-уведомлений.'
        state.value = 'idle'
        return
      }

      let sub = await reg.pushManager.getSubscription()
      if (!sub) {
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        })
      }
      await subscribePush(sub.toJSON() as any)
      state.value = 'enabled'
    } catch (e) {
      console.error('[push] enable failed', e)
      error.value = 'Не удалось включить уведомления.'
      state.value = 'idle'
    }
  }

  async function disable(): Promise<void> {
    if (!supported || isBusy.value) return
    error.value = ''
    state.value = 'unsubscribing'
    try {
      const reg = await ensureRegistration()
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        try { await unsubscribePush(sub.endpoint) } catch { /* best-effort */ }
        await sub.unsubscribe()
      }
      state.value = 'idle'
    } catch (e) {
      console.error('[push] disable failed', e)
      error.value = 'Не удалось отключить уведомления.'
      state.value = 'enabled'
    }
  }

  // Intentionally NOT calling ``refresh()`` on mount. We want the profile
  // page to show notifications as disabled by default ("Включить
  // уведомления") regardless of whether the browser still has an old
  // PushManager subscription lying around — the user must explicitly
  // opt in. ``enable()`` is idempotent and will reuse any existing
  // browser subscription, so a click here re-syncs the backend.

  return {
    state,
    error,
    isEnabled,
    isBusy,
    supported,
    enable,
    disable,
    refresh,
  }
}
