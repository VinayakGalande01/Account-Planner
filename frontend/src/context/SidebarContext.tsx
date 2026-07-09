'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'

export interface ChatSessionInfo {
  id: string
  created_at: string
  title: string
}

interface SidebarContextType {
  isSidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  activeSessionId: string | null
  setActiveSessionId: (id: string | null) => void
  sessions: ChatSessionInfo[]
  loadSessions: () => Promise<void>
  createSession: () => string
  deleteSession: (id: string) => Promise<boolean>
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const { user, authFetch } = useAuth()
  const [isSidebarOpen, setSidebarOpenState] = useState<boolean>(true)
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ChatSessionInfo[]>([])

  // Load sidebar state from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('sidebar_open')
      if (saved !== null) {
        setSidebarOpenState(saved === 'true')
      }
      
      const savedSession = localStorage.getItem('active_session_id')
      if (savedSession) {
        setActiveSessionIdState(savedSession)
      } else {
        setActiveSessionIdState('default_session')
      }
    }
  }, [])

  const setSidebarOpen = (open: boolean) => {
    setSidebarOpenState(open)
    if (typeof window !== 'undefined') {
      localStorage.setItem('sidebar_open', String(open))
    }
  }

  const toggleSidebar = () => {
    setSidebarOpen(!isSidebarOpen)
  }

  const setActiveSessionId = (id: string | null) => {
    setActiveSessionIdState(id)
    if (typeof window !== 'undefined') {
      if (id) {
        localStorage.setItem('active_session_id', id)
      } else {
        localStorage.removeItem('active_session_id')
      }
    }
  }

  const loadSessions = async () => {
    if (!user) return
    try {
      const res = await authFetch('/api/chat/sessions')
      if (res.ok) {
        const data = await res.json()
        setSessions(data || [])
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err)
    }
  }

  const createSession = () => {
    const newId = `session_${Date.now()}`
    setActiveSessionId(newId)
    return newId
  }

  const deleteSession = async (id: string) => {
    if (!user) return false
    
    const isRealSession = sessions.some(s => s.id === id)
    if (!isRealSession) {
      if (activeSessionId === id) {
        setActiveSessionId('default_session')
      }
      return true
    }

    try {
      const res = await authFetch(`/api/chat/sessions/${id}`, {
        method: 'DELETE',
      })
      if (res.ok || res.status === 404) {
        await loadSessions()
        if (activeSessionId === id) {
          const remainingSessions = sessions.filter(s => s.id !== id)
          if (remainingSessions.length > 0) {
            setActiveSessionId(remainingSessions[0].id)
          } else {
            setActiveSessionId('default_session')
          }
        }
        return true
      }
      return false
    } catch (err) {
      console.error('Failed to delete chat session:', err)
      return false
    }
  }

  // Load sessions when user changes
  useEffect(() => {
    if (user) {
      loadSessions()
    } else {
      setSessions([])
      setActiveSessionId('default_session')
    }
  }, [user])

  return (
    <SidebarContext.Provider
      value={{
        isSidebarOpen,
        toggleSidebar,
        setSidebarOpen,
        activeSessionId,
        setActiveSessionId,
        sessions,
        loadSessions,
        createSession,
        deleteSession,
      }}
    >
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider')
  }
  return context
}
