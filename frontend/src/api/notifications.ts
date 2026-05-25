import apiClient from './client'

/** PushSubscription.toJSON() shape — what the browser hands us. */
export interface PushSubscriptionJSON {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

export interface NotificationPreferences {
  edit_notifications_enabled: boolean
}

export interface DocumentNotificationPreferences extends NotificationPreferences {
  document_id: number
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

export const getNotificationPreferences = () =>
  apiClient.get<NotificationPreferences>('/api/notifications/preferences/')

export const updateNotificationPreferences = (editNotificationsEnabled: boolean) =>
  apiClient.patch<NotificationPreferences>('/api/notifications/preferences/', {
    edit_notifications_enabled: editNotificationsEnabled,
  })

export const getDocumentNotificationPreferences = (docId: number) =>
  apiClient.get<DocumentNotificationPreferences>(`/api/notifications/documents/${docId}/preferences/`)

export const updateDocumentNotificationPreferences = (
  docId: number,
  editNotificationsEnabled: boolean,
) =>
  apiClient.patch<DocumentNotificationPreferences>(`/api/notifications/documents/${docId}/preferences/`, {
    edit_notifications_enabled: editNotificationsEnabled,
  })
