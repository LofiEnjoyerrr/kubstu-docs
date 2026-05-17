import apiClient from './client'
import type { Document, DocumentAccess, AvailableDocuments } from '../types'

export const createDocument = (title: string) =>
  apiClient.post<Document>('/api/docs/me/', { title })

export const getAvailableDocuments = () =>
  apiClient.get<AvailableDocuments>('/api/docs/available/')

export const getDocument = (id: number) =>
  apiClient.get<Document>(`/api/docs/${id}/`)

export const updateDocument = (id: number, data: { title?: string; is_public?: boolean }) =>
  apiClient.patch<Document>(`/api/docs/${id}/`, data)

export const getMyAccess = (docId: number) =>
  apiClient.get<{ role: 'owner' | 'editor' | 'viewer' }>(`/api/docs/${docId}/my-access/`)

export const getDocumentAccesses = (docId: number) =>
  apiClient.get<DocumentAccess[]>(`/api/docs/${docId}/accesses/`)

export const createDocumentAccess = (docId: number, userId: number, role: 'viewer' | 'editor') =>
  apiClient.post<DocumentAccess>(`/api/docs/${docId}/accesses/`, { user_id: userId, role })

export const updateDocumentAccess = (docId: number, accessId: number, role: 'viewer' | 'editor') =>
  apiClient.patch<DocumentAccess>(`/api/docs/${docId}/accesses/${accessId}/`, { role })

export const deleteDocumentAccess = (docId: number, accessId: number) =>
  apiClient.delete(`/api/docs/${docId}/accesses/${accessId}/`)

export const searchDocuments = (q: string) =>
  apiClient.get<import('../types').Document[]>('/api/docs/search/', { params: { q } })

export const getComments = (docId: number) =>
  apiClient.get<import('../types').Comment[]>(`/api/docs/${docId}/comments/`)

export const createComment = (docId: number, data: { quote: string; from_pos: number; to_pos: number; content: string }) =>
  apiClient.post<import('../types').Comment>(`/api/docs/${docId}/comments/`, data)

export const updateComment = (
  docId: number,
  commentId: number,
  data: { quote?: string; from_pos?: number; to_pos?: number },
) => apiClient.patch(`/api/docs/${docId}/comments/${commentId}/`, data)

export const deleteComment = (docId: number, commentId: number) =>
  apiClient.delete(`/api/docs/${docId}/comments/${commentId}/`)
