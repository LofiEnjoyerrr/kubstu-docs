import apiClient from './client'
import type { User } from '../types'

export const login = (username: string, password: string) =>
  apiClient.post('/api/users/login/', { username, password })

export const logout = () =>
  apiClient.post('/api/users/logout/')

export const getMe = () =>
  apiClient.get<User>('/api/users/me/')

export const updateMe = (data: FormData | Record<string, unknown>) =>
  apiClient.patch<User>('/api/users/me/', data, {
    headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {},
  })

export const register = (email: string, password: string, username?: string) =>
  apiClient.post('/api/users/register/', { email, password, ...(username ? { username } : {}) })

export const verifyEmail = (token: string) =>
  apiClient.get(`/api/users/email/verify/${token}/`)

export const checkUsernameAvailable = (username: string) =>
  apiClient.get(`/api/users/credentials/username/${username}/available/`)

export const checkEmailAvailable = (email: string) =>
  apiClient.get(`/api/users/credentials/email/${email}/available/`)

export const requestPasswordReset = (email: string) =>
  apiClient.post('/api/users/password-reset/', { email })

export const confirmPasswordReset = (token: string, password: string) =>
  apiClient.post('/api/users/password-reset/confirm/', { token, password })

export const searchUsers = (q: string) =>
  apiClient.get<User[]>('/api/users/search/', { params: { q } })
