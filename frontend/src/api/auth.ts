import apiClient from './client'
import type { User, TokenResponse } from '../types'

export async function register(username: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post('/auth/register', { username, password })
  return data
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post('/auth/login', { username, password })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get('/auth/me')
  return data
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiClient.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}
