'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Send, X, Sparkles } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
}

import { useFocusTrap } from '@/lib/useFocusTrap'
import { useAuth } from '@/context/AuthContext'
import { useSidebar } from '@/context/SidebarContext'

const defaultWelcomeMessage: Message = {
  id: '1',
  type: 'ai',
  content: 'APEX Copilot ready. How can I assist you with your accounts or sales pipeline today?',
  timestamp: new Date(),
}

export function AICopilotPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { authFetch } = useAuth()
  const { activeSessionId } = useSidebar()
  const [messages, setMessages] = useState<Message[]>([defaultWelcomeMessage])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const panelRef = useFocusTrap<HTMLDivElement>({ isOpen, onClose })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text = input) => {
    if (!text.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: text,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const provider = typeof window !== 'undefined' ? (localStorage.getItem('llm_provider') || 'local') : 'local'
      const response = await authFetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-llm-provider': provider,
        },
        body: JSON.stringify({
          query: text,
          session_id: activeSessionId || 'default_copilot_session',
          persona: 'account_manager',
          chat_history: messages.slice(-6).map((m) => ({
            role: m.type === 'user' ? 'user' : 'assistant',
            content: m.content,
          })),
        }),
      })

      if (!response.body) throw new Error('No stream body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullText = ''

      const aiMessageId = (Date.now() + 1).toString()
      setMessages((prev) => [...prev, { id: aiMessageId, type: 'ai', content: '', timestamp: new Date() }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        fullText += chunk
        setMessages((prev) =>
          prev.map((msg) => (msg.id === aiMessageId ? { ...msg, content: fullText } : msg))
        )
      }
    } catch (err) {
      console.error('Copilot stream error:', err)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          type: 'ai',
          content: 'Sorry, I encountered an error connecting to APEX intelligence engine.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Panel */}
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="copilot-panel-title"
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed right-0 top-0 h-screen w-full md:w-96 bg-card border-l border-border shadow-modal flex flex-col z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 id="copilot-panel-title" className="text-lg font-semibold text-foreground">APEX Copilot</h2>
                  <p className="text-xs text-muted-foreground">AI Account Intelligence</p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                aria-label="Close AI Copilot panel"
                className="p-2 hover:bg-input rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-foreground" />
              </motion.button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4" aria-live="polite">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs px-4 py-2.5 rounded-lg text-sm ${
                      message.type === 'user'
                        ? 'bg-primary text-primary-foreground rounded-br-none'
                        : 'bg-background border border-border text-foreground rounded-bl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-xs leading-relaxed">
                      {message.content}
                    </p>
                    <p
                      className={`text-xs mt-1.5 ${
                        message.type === 'user'
                          ? 'text-primary-foreground/70'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </motion.div>
              ))}

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-2 pl-4"
                >
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="w-2 h-2 bg-muted-foreground rounded-full"
                      animate={{ y: [0, -8, 0] }}
                      transition={{ delay: i * 0.1, repeat: Infinity }}
                    />
                  ))}
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-border p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  handleSend()
                }}
                className="flex gap-2"
              >
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about this account..."
                  aria-label="Ask about this account"
                  className="flex-1 bg-input border border-border rounded-lg px-3 py-2 text-sm placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  aria-label="Send query"
                  className="p-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  <Send className="w-4 h-4" />
                </motion.button>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
