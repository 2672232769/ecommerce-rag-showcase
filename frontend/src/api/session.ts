import apiClient from './client'
import type { Session, SessionDetail, Message } from '../types'

export async function createSession(title?: string): Promise<Session> {
  const { data } = await apiClient.post('/sessions', { title: title || '新对话' })
  return data
}

export async function listSessions(): Promise<Session[]> {
  const { data } = await apiClient.get('/sessions')
  return data
}

export async function getSession(id: number): Promise<SessionDetail> {
  const { data } = await apiClient.get(`/sessions/${id}`)
  return data
}

export async function updateSession(id: number, title: string): Promise<Session> {
  const { data } = await apiClient.patch(`/sessions/${id}`, { title })
  return data
}

export async function deleteSession(id: number): Promise<void> {
  await apiClient.delete(`/sessions/${id}`)
}
