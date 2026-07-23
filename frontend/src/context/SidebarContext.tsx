'use client'

/**
 * SIDEBAR NAVIGATION & CHAT SESSION CONTEXT (SidebarContext.tsx)
 * Manages sidebar open/collapse toggle states, chat history sessions, session creation,
 * deletion, and active conversation switching.
 */

// --- SECTION 1: Dependencies & Session Interfaces ---
// Imports React hooks, AuthContext dependencies, and defines ChatSessionInfo type schemas.
import React, { createContext, useContext, useState, useEffect, useRef } from 'react'
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
  isSessionsLoading: boolean
}

// --- SECTION 2: Sidebar Provider State & Session Operations ---
// Provides sidebar collapse state and handles async REST session persistence operations.
const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const { user, authFetch, loading: authLoading } = useAuth()
  const [isSidebarOpen, setSidebarOpenState] = useState<boolean>(true)
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(null)
  const [sessions, setSessions] = useState<ChatSessionInfo[]>([])
  const [isSessionsLoading, setIsSessionsLoading] = useState<boolean>(true)

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

  const latestRequestId = useRef(0)

  const loadSessions = async () => {
    if (authLoading) return
    if (!user) {
      setIsSessionsLoading(false)
      return
    }
    
    latestRequestId.current += 1
    const myRequestId = latestRequestId.current
    
    setIsSessionsLoading(true)

    const fetchWithRetry = async (): Promise<Response> => {
      try {
        const res = await authFetch('/api/chat/sessions')
        if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
        return res
      } catch (err) {
        console.warn('[RETRY] Initial request for chat sessions failed. Retrying in 1s...', err)
        await new Promise(resolve => setTimeout(resolve, 1000))
        const res = await authFetch('/api/chat/sessions')
        if (!res.ok) throw new Error(`Retry failed: ${res.status}`)
        return res
      }
    }

    try {
      const res = await fetchWithRetry()
      const data = await res.json()
      if (myRequestId === latestRequestId.current) {
        setSessions(data || [])
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err)
    } finally {
      if (myRequestId === latestRequestId.current) {
        setIsSessionsLoading(false)
      }
    }
  }

  const createSession = () => {
    const newId = `session_${Date.now()}`
    setActiveSessionId(newId)
    return newId
  }

  const deleteSession = async (id: string) => {
    if (!user) return false
    
    // Always filter out locally immediately so the UI is responsive
    const remainingSessions = sessions.filter(s => s.id !== id)
    setSessions(remainingSessions)
    
    if (activeSessionId === id) {
      if (remainingSessions.length > 0) {
        setActiveSessionId(remainingSessions[0].id)
      } else {
        setActiveSessionId('default_session')
      }
    }

    try {
      const res = await authFetch(`/api/chat/sessions/${id}`, {
        method: 'DELETE',
      })
      
      // Re-sync with database in the background to ensure consistency
      await loadSessions()
      return res.ok || res.status === 404
    } catch (err) {
      console.error('Failed to delete chat session:', err)
      return false
    }
  }

  // Load sessions when user changes
  useEffect(() => {
    if (!authLoading) {
      if (user) {
        loadSessions()
      } else {
        setSessions([])
        setIsSessionsLoading(false)
        setActiveSessionId('default_session')
      }
    }
  }, [user?.id, authLoading])

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
        isSessionsLoading,
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
