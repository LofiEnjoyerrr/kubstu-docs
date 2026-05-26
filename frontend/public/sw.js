// KubSTU Docs service worker — handles Web Push and notification clicks.
//
// Browsers wake this worker even when the site has no open tab and the
// browser app itself is closed, which is what makes "notify the owner on
// their phone" actually possible (the alternative — the in-page
// Notification API — only fires while a tab is alive). The worker is
// served from the site root so its scope covers the whole app.

self.addEventListener('install', (event) => {
  // Activate immediately on first install so the first push subscription
  // can deliver right away without waiting for a reload.
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  // The backend ships a small JSON payload — title, body, tag, doc_id.
  // If anything is missing or parsing fails we still show a generic
  // notification, because dropping the event would leave the browser
  // with no UI and Chrome would penalize us with a permission warning.
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch (_) {
    payload = { title: 'KubSTU Docs', body: event.data ? event.data.text() : '' }
  }

  const title = payload.title || 'KubSTU Docs'
  const body = payload.body || 'Документ был изменён'
  const tag = payload.tag || 'kubstu-docs'

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag,
      renotify: true,
      icon: '/doc-icon.svg',
      badge: '/doc-icon.svg',
      // Carry the doc id through to the click handler so we can deep-link.
      data: { doc_id: payload.doc_id ?? null },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const docId = event.notification.data && event.notification.data.doc_id
  const targetPath = docId ? `/documents/${docId}` : '/dashboard'

  event.waitUntil((async () => {
    const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    // If a tab is already open on the same origin, focus + navigate it
    // instead of spawning a new one — Chrome on Android otherwise opens
    // a second copy of the PWA which is jarring.
    for (const client of allClients) {
      try {
        await client.navigate(targetPath)
        return client.focus()
      } catch (_) { /* navigate may fail across origins; fall through */ }
    }
    if (self.clients.openWindow) {
      return self.clients.openWindow(targetPath)
    }
  })())
})
