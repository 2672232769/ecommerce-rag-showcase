export interface User {
  id: number
  username: string
  role: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Session {
  id: number
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  sources: Source[] | null
  created_at: string
}

export interface Source {
  source: string
  content: string
}

export interface SessionDetail {
  id: number
  title: string
  created_at: string
  updated_at: string
  messages: Message[]
}

export interface KnowledgeDocument {
  id: number
  filename: string
  file_type: string
  file_size: number
  chunk_count: number
  uploaded_at: string
}
