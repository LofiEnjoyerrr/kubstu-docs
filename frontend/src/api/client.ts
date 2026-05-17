import axios from 'axios'

function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

const apiClient = axios.create({
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase() ?? ''
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    config.headers['X-CSRFToken'] = getCsrfToken()
  }
  return config
})

export default apiClient
