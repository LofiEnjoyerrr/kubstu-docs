import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Document, DocumentAccess } from '../types'
import * as docsApi from '../api/documents'

export const useDocumentsStore = defineStore('documents', () => {
  const ownerDocuments = ref<Document[]>([])
  const openedDocuments = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const accesses = ref<DocumentAccess[]>([])

  async function fetchAvailable() {
    const res = await docsApi.getAvailableDocuments()
    ownerDocuments.value = res.data.owner_documents
    openedDocuments.value = res.data.opened_documents
  }

  async function fetchDocument(id: number) {
    const res = await docsApi.getDocument(id)
    currentDocument.value = res.data
    return res.data
  }

  async function createDocument(title: string) {
    const res = await docsApi.createDocument(title)
    ownerDocuments.value.unshift(res.data)
    return res.data
  }

  async function deleteDocument(id: number) {
    await docsApi.deleteDocument(id)
    ownerDocuments.value = ownerDocuments.value.filter((d) => d.id !== id)
    openedDocuments.value = openedDocuments.value.filter((d) => d.id !== id)
    if (currentDocument.value?.id === id) currentDocument.value = null
  }

  async function updateDocument(
    id: number,
    data: {
      title?: string
      is_public?: boolean
      status_text?: string
      status_color?: string
      content?: string
      page_width?: number
      page_height?: number
      margin_top?: number
      margin_right?: number
      margin_bottom?: number
      margin_left?: number
      header_content?: string
      footer_content?: string
      show_page_numbers?: boolean
      page_number_start?: number
    },
  ) {
    const res = await docsApi.updateDocument(id, data)
    currentDocument.value = res.data
    const idx = ownerDocuments.value.findIndex((d) => d.id === id)
    if (idx !== -1) ownerDocuments.value[idx] = res.data
    return res.data
  }

  async function fetchAccesses(docId: number) {
    const res = await docsApi.getDocumentAccesses(docId)
    accesses.value = res.data
  }

  async function addAccess(docId: number, userId: number, role: 'viewer' | 'editor') {
    const res = await docsApi.createDocumentAccess(docId, userId, role)
    accesses.value.push(res.data)
    return res.data
  }

  async function updateAccess(docId: number, accessId: number, role: 'viewer' | 'editor') {
    const res = await docsApi.updateDocumentAccess(docId, accessId, role)
    const idx = accesses.value.findIndex((a) => a.id === accessId)
    if (idx !== -1) accesses.value[idx] = res.data
  }

  async function removeAccess(docId: number, accessId: number) {
    await docsApi.deleteDocumentAccess(docId, accessId)
    accesses.value = accesses.value.filter((a) => a.id !== accessId)
  }

  return {
    ownerDocuments,
    openedDocuments,
    currentDocument,
    accesses,
    fetchAvailable,
    fetchDocument,
    createDocument,
    deleteDocument,
    updateDocument,
    fetchAccesses,
    addAccess,
    updateAccess,
    removeAccess,
  }
})
