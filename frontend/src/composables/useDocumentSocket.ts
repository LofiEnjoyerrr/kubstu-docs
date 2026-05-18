import { ref, onUnmounted } from 'vue'
import type { CollaboratorInfo, Comment, PageLayout } from '../types'

type InitCallback = (data: { content: unknown; version: number; users: CollaboratorInfo[] }) => void
type EditCallback = (data: { delta: unknown; version: number; user_id: number; username: string; color: string }) => void
type CursorCallback = (data: { user_id: number; username: string; color: string; position: { from: number; to: number } }) => void
type UserLeaveCallback = (userId: number | null) => void
type CommentAddCallback = (comment: Comment) => void
type CommentDeleteCallback = (commentId: number) => void
type CommentUpdateCallback = (comment: Comment) => void
type FullReplaceCallback = (data: { content: unknown; version: number; user_id: number | null }) => void
type PageLayoutCallback = (layout: PageLayout) => void

export function useDocumentSocket(docId: number) {
  const ws = ref<WebSocket | null>(null)
  const collaborators = ref<CollaboratorInfo[]>([])
  const serverVersion = ref(0)
  const isConnected = ref(false)

  let onInitCb: InitCallback | null = null
  let onEditCb: EditCallback | null = null
  let onCursorCb: CursorCallback | null = null
  let onUserLeaveCb: UserLeaveCallback | null = null
  let onCommentAddCb: CommentAddCallback | null = null
  let onCommentDeleteCb: CommentDeleteCallback | null = null
  let onCommentUpdateCb: CommentUpdateCallback | null = null
  let onFullReplaceCb: FullReplaceCallback | null = null
  let onPageLayoutCb: PageLayoutCallback | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function buildWsUrl() {
    const base: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
    const wsBase = base.replace(/^http/, 'ws')
    return `${wsBase}/ws/docs/${docId}/`
  }

  function connect() {
    ws.value = new WebSocket(buildWsUrl())

    ws.value.onopen = () => {
      isConnected.value = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.value.onclose = () => {
      isConnected.value = false
      reconnectTimer = setTimeout(connect, 3000)
    }

    ws.value.onerror = () => {
      ws.value?.close()
    }

    ws.value.onmessage = (event: MessageEvent) => {
      try {
        handleMessage(JSON.parse(event.data as string))
      } catch {
        // ignore malformed frames
      }
    }
  }

  function handleMessage(data: Record<string, unknown>) {
    switch (data.type) {
      case 'init':
        serverVersion.value = data.version as number
        collaborators.value = (data.users as CollaboratorInfo[]) ?? []
        onInitCb?.(data as Parameters<InitCallback>[0])
        break

      case 'edit':
        serverVersion.value = data.version as number
        onEditCb?.(data as Parameters<EditCallback>[0])
        break

      case 'cursor':
        onCursorCb?.(data as Parameters<CursorCallback>[0])
        break

      case 'user_join': {
        const id = data.user_id as number | null
        if (!collaborators.value.find((c) => c.user_id === id)) {
          collaborators.value.push({
            user_id: id,
            username: data.username as string,
            color: data.color as string,
            avatar: (data.avatar as string | null | undefined) ?? null,
          })
        }
        break
      }

      case 'user_leave': {
        const leaveId = data.user_id as number | null
        collaborators.value = collaborators.value.filter((c) => c.user_id !== leaveId)
        onUserLeaveCb?.(leaveId)
        break
      }

      case 'comment_add':
        onCommentAddCb?.(data.comment as Comment)
        break

      case 'comment_delete':
        onCommentDeleteCb?.(data.comment_id as number)
        break

      case 'comment_update':
        onCommentUpdateCb?.(data.comment as Comment)
        break

      case 'full_replace':
        serverVersion.value = data.version as number
        onFullReplaceCb?.(data as Parameters<FullReplaceCallback>[0])
        break

      case 'page_layout':
        onPageLayoutCb?.({
          page_width: data.page_width as number,
          margin_top: data.margin_top as number,
          margin_right: data.margin_right as number,
          margin_bottom: data.margin_bottom as number,
          margin_left: data.margin_left as number,
        })
        break
    }
  }

  function sendEdit(delta: unknown, state: unknown) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(
        JSON.stringify({ type: 'edit', delta, state, version: serverVersion.value }),
      )
    }
  }

  function sendCursor(from: number, to: number) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'cursor', position: { from, to } }))
    }
  }

  function onInit(cb: InitCallback) { onInitCb = cb }
  function onEdit(cb: EditCallback) { onEditCb = cb }
  function onCursor(cb: CursorCallback) { onCursorCb = cb }
  function onUserLeave(cb: UserLeaveCallback) { onUserLeaveCb = cb }
  function onCommentAdd(cb: CommentAddCallback) { onCommentAddCb = cb }
  function onCommentDelete(cb: CommentDeleteCallback) { onCommentDeleteCb = cb }
  function onCommentUpdate(cb: CommentUpdateCallback) { onCommentUpdateCb = cb }
  function onFullReplace(cb: FullReplaceCallback) { onFullReplaceCb = cb }
  function onPageLayout(cb: PageLayoutCallback) { onPageLayoutCb = cb }

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (ws.value) {
      // Null out all handlers BEFORE close() so the onclose callback
      // doesn't schedule a reconnect when we intentionally leave.
      ws.value.onopen = null
      ws.value.onclose = null
      ws.value.onerror = null
      ws.value.onmessage = null
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
  }

  onUnmounted(disconnect)

  return {
    connect, disconnect, sendEdit, sendCursor,
    onInit, onEdit, onCursor, onUserLeave, onCommentAdd, onCommentDelete, onCommentUpdate,
    onFullReplace, onPageLayout,
    collaborators, serverVersion, isConnected,
  }
}
