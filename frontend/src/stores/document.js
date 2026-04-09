import { defineStore } from 'pinia'
import api from '@/axios'

export const useDocumentStore = defineStore('document', {
  actions: {
    async createDocument(title) {
      const { data } = await api.post('/api/docs/me/', {
        title: title,
      })

      return data;
    },

    async fetchDocuments() {
      const { data } = await api.get('/api/docs/available/')

      return data;
    },

    async fetchDocument(id) {
      const { data } = await api.get(`/api/docs/${id}/`)

      return data;
    },
  },
})
