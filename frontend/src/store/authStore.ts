import { create } from 'zustand'
import * as authApi from '../api/auth'
import type { User } from '../types'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<boolean>
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: false,
  isLoading: true,

  login: async (username, password) => {
    const res = await authApi.login(username, password)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    set({ user: res.user, token: res.access_token, isAuthenticated: true })
  },

  register: async (username, password) => {
    const res = await authApi.register(username, password)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    set({ user: res.user, token: res.access_token, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null, isAuthenticated: false })
  },

  checkAuth: async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      set({ isLoading: false, isAuthenticated: false })
      return false
    }
    try {
      const user = await authApi.getMe()
      set({ user, token, isAuthenticated: true, isLoading: false })
      return true
    } catch {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      set({ user: null, token: null, isAuthenticated: false, isLoading: false })
      return false
    }
  },

  changePassword: async (oldPassword, newPassword) => {
    await authApi.changePassword(oldPassword, newPassword)
  },
}))
