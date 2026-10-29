import type { KnowledgeDocument } from '../types'
import apiClient from './client'

export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  const { data } = await apiClient.get('/knowledge/documents')
  return data
}

export async function deleteDocument(id: number): Promise<void> {
  await apiClient.delete(`/knowledge/documents/${id}`)
}
