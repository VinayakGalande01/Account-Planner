'use client'

// APEX Intelligence chat page: conversational AI assistant over account data,
// with session history, streaming responses, and structured contract rendering.
// Major sections below:
//   - SECTION: Session Message Loading
//   - SECTION: Send Message / Streaming Handler
//   - SECTION: Render - Header & Persona Controls
//   - SECTION: Render - Sessions Drawer & Chat Messages

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import { Brain, Send, Zap, Plus, MessageSquare, Trash2, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react'
import { ContractRenderer, FinalizedContractRenderer } from '@/components/apex-widgets'
import { parseResponseContract } from '@/utils/contractParser'
import type { ResponseContract, RecommendedAction } from '@/types/responseContract'

import { useAuth } from '@/context/AuthContext'
import { useSidebar } from '@/context/SidebarContext'
import { useAnimation } from '@/context/AnimationContext'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/PageHeader'
import { ThinkingIndicator } from '@/components/ThinkingIndicator'
import { ReasoningTrail } from '@/components/ReasoningTrail'

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  contract?: ResponseContract;
  reasoningSteps?: string[];
}

function RenderMessageLines({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <>
      {lines.map((line, idx) => (
        <div key={idx} className={idx === lines.length - 1 ? "new-stream-line min-h-[16px]" : "min-h-[16px]"}>
          {line}
        </div>
      ))}
    </>
  )
}

const initialMessages: Message[] = [
  {
    id: 1,
    role: 'assistant',
    content: 'APEX is ready. Client list loaded. How can I help you today?',
    timestamp: new Date(),
  },
]

const suggestedPrompts = [
  'Show me accounts at high risk',
  'Which accounts have the most potential?',
  'Analyze sales velocity trends',
  'Recommend next actions for top accounts',
]

export default function IntelligencePage() {
  const { authFetch, user } = useAuth()
  const { activeSessionId, setActiveSessionId, sessions, loadSessions, createSession, deleteSession, isSessionsLoading } = useSidebar()
  const { isFirstVisit } = useAnimation()
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [persona, setPersona] = useState<'account_manager' | 'vp_sales' | 'executive'>('account_manager')
  const [isLoading, setIsLoading] = useState(false)
  const [isSessionLoading, setIsSessionLoading] = useState(false)
  const [isHistoryOpen, setIsHistoryOpen] = useState(true)
  const [currentStatus, setCurrentStatus] = useState('')
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const [mounted, setMounted] = useState(false)

  const handleActionClick = (action: RecommendedAction) => {
    if (!isLoading) {
      // Pass action_type directly to bypass intent classifier on chip click.
      // Pass activeAccount as override so chips always use the current session's
      // resolved account — not a stale or null value from a different turn.
      handleSendMessage(action.title, {
        action_type: action.action_type ?? null,
        override_account: action.source_account ?? activeAccount,
      })
    }
  }

  useEffect(() => {
    setMounted(true)
  }, [])

  // --- SECTION: Session Message Loading ---
  // Load session messages when activeSessionId changes
  useEffect(() => {
    let active = true
    const abortController = new AbortController()

    const fetchSessionMessages = async () => {
      // Bypasses the fetch & skeleton state if there is no real history to load
      const isRealSession = activeSessionId && activeSessionId !== 'default_session'
      
      if (!isRealSession) {
        if (active) {
          setMessages(initialMessages)
          setIsSessionLoading(false)
        }
        return
      }

      setIsSessionLoading(true)
      const startTime = Date.now()

      try {
        const res = await authFetch(`/api/chat/sessions/${activeSessionId}/messages`, {
          signal: abortController.signal
        })
        if (res.ok && active) {
          const data = await res.json()
          if (Array.isArray(data) && data.length > 0) {
            const formatted = data.map((msg: any) => {
              const lines = (msg.content || '').split('\n')
              const cleanLines: string[] = []
              const steps: string[] = []
              lines.forEach((line: string) => {
                if (line.startsWith('sys_meta_log|')) {
                  steps.push(line.replace('sys_meta_log|', '').trim())
                } else {
                  cleanLines.push(line)
                }
              })
              const cleanContent = cleanLines.join('\n')
              return {
                id: msg.id || Date.now(),
                role: msg.role as 'user' | 'assistant',
                content: cleanContent,
                timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                contract: parseResponseContract(cleanContent).isStructured ? parseResponseContract(cleanContent) : undefined,
                reasoningSteps: steps.length > 0 ? steps : undefined
              }
            })
            setMessages(formatted)
          } else {
            setMessages(initialMessages)
          }
        } else if (active) {
          setMessages(initialMessages)
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error('Error fetching session messages:', err)
          if (active) {
            setMessages(initialMessages)
          }
        }
      } finally {
        if (active) {
          // Ensures loading skeleton displays for at least 450ms to prevent flickering
          const elapsed = Date.now() - startTime
          const delay = Math.max(0, 450 - elapsed)
          
          if (delay > 0) {
            setTimeout(() => {
              if (active) setIsSessionLoading(false)
            }, delay)
          } else {
            setIsSessionLoading(false)
          }
        }
      }
    }

    if (mounted) {
      fetchSessionMessages()
    }
    return () => {
      active = false
      abortController.abort()
    }
  }, [activeSessionId, mounted])

  const [sessionId] = useState(() => Math.random().toString(36).substring(2, 15))
  const [activeAccount, setActiveAccount] = useState<string | null>(null)

  // --- SECTION: Send Message / Streaming Handler ---
  const handleSendMessage = async (
    text = inputValue,
    overrides?: { action_type?: string | null; override_account?: string | null }
  ) => {
    if (!text.trim() || isLoading) return

    // Add user message
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    setCurrentStatus('')
    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const provider = typeof window !== 'undefined' ? (localStorage.getItem('llm_provider') || 'local') : 'local'
      const response = await authFetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-llm-provider': provider
        },
        body: JSON.stringify({
          query: text,
          session_id: activeSessionId || 'default_session',
          // Use override_account (from chip) if provided, otherwise fall back to current activeAccount state.
          // This guarantees chip clicks always reference the last resolved account (e.g. Airbus SE),
          // not a null or stale value.
          active_account: overrides?.override_account ?? activeAccount,
          persona: persona,
          // Pass action_type directly so the backend dispatcher skips intent classification for chip clicks.
          ...(overrides?.action_type ? { action_type: overrides.action_type } : {}),
          chat_history: messages.slice(-10).map(m => ({
            role: m.role,
            content: m.content
          }))
        }),
      })

      if(!response.body) throw new Error('No stream body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullText = ''
      let currentBuffer = ''
      const accumulatedSteps: string[] = []
      let lastWasMeta = false

      const aiMessageId = Date.now() + 1
      setMessages((prev) => [...prev, { id: aiMessageId, role: 'assistant', content: '', timestamp: new Date(), reasoningSteps: [] }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        
        currentBuffer += chunk
        
        // Process full lines inside the buffer
        while (currentBuffer.includes('\n')) {
          const newlineIndex = currentBuffer.indexOf('\n')
          const line = currentBuffer.substring(0, newlineIndex).trim()
          currentBuffer = currentBuffer.substring(newlineIndex + 1)

          if (line.startsWith('sys_meta_log|')) {
            lastWasMeta = true
            const statusMsg = line.replace('sys_meta_log|', '').trim()
            if (statusMsg) {
              setCurrentStatus(statusMsg)
              accumulatedSteps.push(statusMsg)
              
              // Extract active account from meta log if available
              if (statusMsg.includes('Active Account:')) {
                const match = statusMsg.match(/Active Account:\s*(.*)/)
                if (match) {
                  setActiveAccount(match[1].trim())
                }
              }
            }
          } else {
            // Keep normal text lines
            if (line.trim() === '' && lastWasMeta) {
              // Skip empty lines immediately following progress logs
            } else {
              fullText += line + '\n'
              lastWasMeta = false
            }
          }
        }

        // Live update the message container with clean text and accumulated steps
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? {
                  ...msg,
                  content: fullText + (currentBuffer.startsWith('sys_meta_log|') ? '' : currentBuffer),
                  reasoningSteps: [...accumulatedSteps],
                }
              : msg
          )
        )
      }

      // Handle any remaining content left in buffer
      if (currentBuffer) {
        if (currentBuffer.startsWith('sys_meta_log|')) {
          const statusMsg = currentBuffer.replace('sys_meta_log|', '').trim()
          if (statusMsg) {
            setCurrentStatus(statusMsg)
            accumulatedSteps.push(statusMsg)
          }
        } else {
          fullText += currentBuffer
        }
      }

      // Finish by parsing response contracts
      const contract = parseResponseContract(fullText.trim())
      setMessages((prev) => prev.map(msg =>
        msg.id === aiMessageId
          ? {
              ...msg,
              content: fullText.trim(),
              contract: contract.isStructured ? contract : undefined,
              reasoningSteps: accumulatedSteps.length > 0 ? accumulatedSteps : undefined
            }
          : msg
      ))

      // Refresh sidebar sessions to show generated title for the session
      setTimeout(() => {
        loadSessions()
      }, 500)
    } catch (error) {
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Error: Could not connect to the AI.',
        timestamp: new Date(),
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <main className="flex-1 overflow-y-auto flex flex-col">
      <div className="flex-1 p-6 md:p-8 flex flex-col min-h-0">
        {/* --- SECTION: Render - Header & Persona Controls --- */}
        <PageHeader
          title="Intelligence"
          subtitle="APEX V2.1 - Connected | Ask me anything about your accounts"
          icon={<Brain className="w-6 h-6" />}
          action={
            <div className="flex flex-wrap items-center gap-3">
              {/* Persona Selector (Top-of-Page Placement) */}
              <div className="flex bg-secondary/50 border border-border p-1 rounded-full" role="group" aria-label="Select AI persona view">
                <button
                  onClick={() => setPersona('account_manager')}
                  aria-pressed={persona === 'account_manager'}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                    persona === 'account_manager'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  AM
                </button>
                <button
                  onClick={() => setPersona('vp_sales')}
                  aria-pressed={persona === 'vp_sales'}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                    persona === 'vp_sales'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  VP Sales
                </button>
                <button
                  onClick={() => setPersona('executive')}
                  aria-pressed={persona === 'executive'}
                  className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                    persona === 'executive'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Executive
                </button>
              </div>

              {/* History Toggle Button */}
              <button
                onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                aria-label={isHistoryOpen ? "Collapse history panel" : "Expand history panel"}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-border rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
              >
                {isHistoryOpen ? <ChevronLeft className="w-4 h-4" aria-hidden="true" /> : <ChevronRight className="w-4 h-4" aria-hidden="true" />}
                <span>{isHistoryOpen ? 'Hide History' : 'Show History'}</span>
              </button>
            </div>
          }
        />

        {/* --- SECTION: Render - Sessions Drawer & Chat Messages --- */}
        {/* 2-Column Layout with Page-Scoped Session History */}
        <div className="flex-1 flex gap-6 min-h-0 overflow-hidden">
          {/* Conversation Sessions Drawer */}
          {isHistoryOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 256, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="w-64 bg-card border border-border rounded-lg p-4 flex flex-col shrink-0 overflow-hidden"
            >
              <div className="flex items-center justify-between mb-3 pb-3 border-b border-border">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Conversations</span>
                <button
                  onClick={() => createSession()}
                  aria-label="Create new chat session"
                  className="flex items-center gap-1 px-2 py-1 bg-primary text-primary-foreground text-xs font-semibold rounded hover:bg-primary/90 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>New</span>
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
                {isSessionsLoading ? (
                  <div className="space-y-2 p-1">
                    <Skeleton className="h-8 w-full rounded-md" />
                    <Skeleton className="h-8 w-full rounded-md" />
                    <Skeleton className="h-8 w-full rounded-md" />
                  </div>
                ) : sessions.length === 0 ? (
                  <p className="text-xs text-muted-foreground/60 italic p-2">No past conversations</p>
                ) : (
                  <AnimatePresence initial={false}>
                    {sessions.map((session) => (
                      <motion.div
                        key={session.id}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0, transition: { duration: 0.2 } }}
                        className={`group relative flex items-center justify-between rounded-md text-xs overflow-hidden transition-colors ${
                          activeSessionId === session.id
                            ? 'bg-primary/10 text-primary font-medium border border-primary/20'
                            : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
                        }`}
                      >
                        <button
                          onClick={() => setActiveSessionId(session.id)}
                          className="flex-1 text-left px-2.5 py-2 truncate flex items-center gap-2 min-w-0"
                        >
                          <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-70" aria-hidden="true" />
                          <span className="truncate flex-1">{session.title}</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSessionToDelete(session.id)
                          }}
                          aria-label={`Delete ${session.title}`}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-muted-foreground hover:text-red-400 transition-opacity mr-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                )}
              </div>
            </motion.div>
          )}

          {/* Main Intelligence Chat Area */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Messages */}
            <motion.div
              initial={isFirstVisit ? { opacity: 0 } : false}
              animate={{ opacity: 1 }}
              transition={{ delay: isFirstVisit ? 0.1 : 0, duration: 0.4 }}
              className="flex-1 bg-card border border-border rounded-lg p-5 mb-4 overflow-y-auto"
            >
          <div className="space-y-4 flex flex-col">
            {isSessionLoading ? (
              <div className="flex flex-col gap-6 p-4 select-none">
                {/* Labeled Progress Caption */}
                <div className="flex items-center gap-2.5 justify-center py-2 bg-secondary/20 border border-border rounded-lg max-w-sm mx-auto w-full">
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin shrink-0" />
                  <span className="text-xs font-semibold text-muted-foreground">Retrieving conversation history...</span>
                </div>

                {/* Alternating Realistic Chat Rows Skeletons */}
                <div className="space-y-5 mt-2">
                  {/* Row 1: Assistant Message (Left) */}
                  <div className="flex items-start gap-3 justify-start max-w-xl">
                    <Skeleton className="w-8 h-8 rounded-full shrink-0" />
                    <div className="bg-secondary/40 border border-border rounded-lg p-3 w-full space-y-2">
                      <Skeleton className="h-3 w-3/4 rounded" />
                      <Skeleton className="h-3 w-1/2 rounded" />
                    </div>
                  </div>

                  {/* Row 2: User Message (Right) */}
                  <div className="flex items-start gap-3 justify-end max-w-md ml-auto">
                    <div className="bg-primary/10 border border-primary/20 rounded-lg p-3 w-full space-y-2">
                      <Skeleton className="h-3 w-5/6 rounded bg-primary/20" />
                      <Skeleton className="h-3 w-2/3 rounded bg-primary/20" />
                    </div>
                    <Skeleton className="w-8 h-8 rounded-full shrink-0 bg-primary/20" />
                  </div>

                  {/* Row 3: Assistant Message (Left) */}
                  <div className="flex items-start gap-3 justify-start max-w-2xl">
                    <Skeleton className="w-8 h-8 rounded-full shrink-0" />
                    <div className="bg-secondary/40 border border-border rounded-lg p-3 w-full space-y-2">
                      <Skeleton className="h-3 w-11/12 rounded" />
                      <Skeleton className="h-3 w-4/5 rounded" />
                      <Skeleton className="h-3 w-1/3 rounded" />
                    </div>
                  </div>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Brain className="w-12 h-12 text-primary/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">Start a conversation...</p>
                </div>
              </div>
            ) : (
              messages.map((message, index) => {
                if (message.role === 'assistant' && !message.content.trim() && (!message.reasoningSteps || message.reasoningSteps.length === 0)) {
                  return null
                }
                return (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`px-4 py-2 rounded-lg ${message.role === 'user'
                        ? 'max-w-lg bg-primary text-primary-foreground'
                        : (message.contract || message.content.includes('__SECTION_'))
                          ? 'max-w-6xl bg-secondary/50 text-foreground border border-border w-full'
                          : 'max-w-2xl bg-secondary/50 text-foreground border border-border w-fit'
                        }`}
                    >
                    {message.role === 'assistant' && (
                      <ReasoningTrail steps={message.reasoningSteps || []} />
                    )}
                    {message.role === 'assistant' ? (
                      message.contract ? (
                        <FinalizedContractRenderer contract={message.contract} onActionClick={handleActionClick} />
                      ) : message.content.includes('__SECTION_') ? (
                        <ContractRenderer content={message.content} isStreaming={isLoading && index === messages.length - 1} onActionClick={handleActionClick} />
                      ) : (
                        <div className="text-sm leading-relaxed">
                          {(() => {
                            try {
                              const p = JSON.parse(message.content);
                              if (p.type === 'conversational' || p.type === 'clarification') {
                                return <FinalizedContractRenderer contract={{ isStructured: true, type: p.type, conversationalData: p } as any} onActionClick={handleActionClick} />;
                              }
                            } catch (e) { }
                            return (
                              <>
                                <RenderMessageLines content={message.content} />
                                {isLoading && index === messages.length - 1 && (
                                  <span className="inline-block w-[2px] h-4 bg-primary ml-0.5 animate-pulse align-middle rounded-full" />
                                )}
                              </>
                            );
                          })()}
                        </div>
                      )
                    ) : (
                      <p className="text-sm">{message.content}</p>
                    )}
                    <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>
                      {mounted ? message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </p>
                  </div>
                </motion.div>
                )
              })
            )}

            {isLoading && currentStatus && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="flex justify-start"
              >
                <ThinkingIndicator status={currentStatus} />
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Suggested prompts (only show initially) */}
        {messages.length === 1 && (
          <motion.div
            initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: isFirstVisit ? 0.2 : 0, duration: 0.4 }}
            className="mb-4"
          >
            <p className="text-xs text-muted-foreground mb-2">Suggested questions:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {suggestedPrompts.map((prompt, index) => (
                <motion.button
                  key={prompt}
                  initial={isFirstVisit ? { opacity: 0, x: -10 } : false}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: isFirstVisit ? 0.25 + index * 0.05 : 0 }}
                  onClick={() => handleSendMessage(prompt)}
                  className="flex items-start gap-2 px-3 py-2 bg-secondary/30 border border-border rounded-md hover:bg-secondary/50 transition-colors text-sm text-foreground text-left"
                >
                  <Zap className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span>{prompt}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Input area */}
        <motion.div
          initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: isFirstVisit ? 0.15 : 0, duration: 0.4 }}
          className="flex flex-col gap-2 w-full"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="flex gap-3"
          >
            <input
              type="text"
              placeholder="Ask a question about your accounts..."
              aria-label="Ask a question about your accounts"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
              className="flex-1 bg-secondary border border-border rounded-lg px-4 py-2.5 text-sm placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              aria-label="Send message"
              className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
            </button>
          </form>
        </motion.div>
      </div>
      </div>
      </div>
    </main>

      {/* Custom Premium Delete Confirmation Modal */}
      <AnimatePresence>
        {sessionToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop Blur Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSessionToDelete(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            
            {/* Modal Card */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 12 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 12 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="relative w-full max-w-sm bg-card border border-border rounded-xl shadow-modal overflow-hidden p-5 z-50 text-foreground"
            >
              <div className="flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-5 h-5 text-red-500" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold tracking-tight text-foreground">
                    Delete Chat Session?
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                    Are you sure you want to delete this chat session? This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 mt-5">
                <button
                  onClick={() => setSessionToDelete(null)}
                  disabled={isDeleting}
                  className="px-3 py-1.5 border border-border text-xs font-semibold rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (sessionToDelete) {
                      setIsDeleting(true)
                      await deleteSession(sessionToDelete)
                      setIsDeleting(false)
                      setSessionToDelete(null)
                    }
                  }}
                  disabled={isDeleting}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded-md hover:bg-red-500 transition-colors shadow-flat disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isDeleting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin shrink-0" />
                      <span>Deleting...</span>
                    </>
                  ) : (
                    <span>Delete Session</span>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
