import { ref, onUnmounted } from 'vue'
import type { CollaboratorInfo, Comment } from '../types'

type InitCallback = (data: { content: unknown; version: number; users: CollaboratorInfo[] }) => void
type EditCallback = (data: { delta: unknown; version: number; user_id: number; username: string; color: string }) => void
type CursorCallback = (data: { user_id: number; username: string; color: string; position: { from: number; to: number } }) => void
type UserLeaveCallback = (userId: number | null) => void
type CommentAddCallback = (comment: Comment) => void
type CommentDeleteCallback = (commentId: number) => void

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

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    ws.value?.close()
    ws.value = null
  }

  onUnmounted(disconnect)

  return {
    connect, disconnect, sendEdit, sendCursor,
    onInit, onEdit, onCursor, onUserLeave, onCommentAdd, onCommentDelete,
    collaborators, serverVersion, isConnected,
  }
}
