import { create } from 'zustand'
import * as sessionApi from '../api/session'
import type { Session, Message } from '../types'

interface SessionState {
  sessions: Session[]
  currentSessionId: number | null
  isLoading: boolean
  loadSessions: () => Promise<void>
  createSession: () => Promise<Session>
  deleteSession: (id: number) => Promise<void>
  updateSessionTitle: (id: number, title: string) => Promise<void>
  setCurrentSession: (id: number | null) => void
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  isLoading: false,

  loadSessions: async () => {
    set({ isLoading: true })
    try {
      const sessions = await sessionApi.listSessions()
      set({ sessions, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  createSession: async () => {
    const session = await sessionApi.createSession('新对话')
    set((state) => ({ sessions: [session, ...state.sessions] }))
    return session
  },

  deleteSession: async (id) => {
    await sessionApi.deleteSession(id)
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      currentSessionId:
        state.currentSessionId === id ? null : state.currentSessionId,
    }))
  },

  updateSessionTitle: async (id, title) => {
    const updated = await sessionApi.updateSession(id, title)
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? updated : s)),
    }))
  },

  setCurrentSession: (id) => set({ currentSessionId: id }),
}))
