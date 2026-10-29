import { create } from 'zustand'
import * as sessionApi from '../api/session'
import type { Message, Source } from '../types'

interface ChatState {
  messages: Message[]
  isLoading: boolean
  streamingContent: string
  currentSources: Source[] | null

  loadMessages: (sessionId: number) => Promise<void>
  addUserMessage: (content: string) => void
  startStreaming: () => void
  setSources: (sources: Source[]) => void
  appendChunk: (chunk: string) => void
  finishStreaming: (messageId: number) => void
  clearChat: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  streamingContent: '',
  currentSources: null,

  loadMessages: async (sessionId) => {
    try {
      const detail = await sessionApi.getSession(sessionId)
      set({ messages: detail.messages })
    } catch {
      set({ messages: [] })
    }
  },

  addUserMessage: (content) => {
    const userMsg: Message = {
      id: Date.now(),
      session_id: 0,
      role: 'user',
      content,
      sources: null,
      created_at: new Date().toISOString(),
    }
    set((state) => ({ messages: [...state.messages, userMsg] }))
  },

  startStreaming: () => {
    set({ isLoading: true, streamingContent: '', currentSources: null })
  },

  setSources: (sources) => {
    set({ currentSources: sources })
  },

  appendChunk: (chunk) => {
    set((state) => ({ streamingContent: state.streamingContent + chunk }))
  },

  finishStreaming: (messageId) => {
    const state = get()
    if (!state.streamingContent) {
      set({ isLoading: false })
      return
    }
    const aiMsg: Message = {
      id: messageId,
      session_id: 0,
      role: 'assistant',
      content: state.streamingContent,
      sources: state.currentSources,
      created_at: new Date().toISOString(),
    }
    set((state) => ({
      messages: [...state.messages, aiMsg],
      isLoading: false,
      streamingContent: '',
      currentSources: null,
    }))
  },

  clearChat: () => {
    set({
      messages: [],
      isLoading: false,
      streamingContent: '',
      currentSources: null,
    })
  },
}))
