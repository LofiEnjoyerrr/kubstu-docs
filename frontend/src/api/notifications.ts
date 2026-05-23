import apiClient from './client'

/** PushSubscription.toJSON() shape — what the browser hands us. */
export interface PushSubscriptionJSON {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

export async function fetchVapidPublicKey(): Promise<string> {
  const { data } = await apiClient.get<{ public_key: string }>(
    '/api/notifications/vapid-public-key/',
  )
  return data.public_key
}

export async function subscribePush(sub: PushSubscriptionJSON): Promise<void> {
  await apiClient.post('/api/notifications/subscribe/', sub)
}

export async function unsubscribePush(endpoint: string): Promise<void> {
  await apiClient.post('/api/notifications/unsubscribe/', { endpoint })
}
