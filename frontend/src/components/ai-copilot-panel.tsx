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

const initialMessages: Message[] = [
  {
    id: '1',
    type: 'ai',
    content:
      'I&apos;m APEX Copilot. I can help you with account intelligence, risk analysis, and deal progression insights. What would you like to know about Acme Corp?',
    timestamp: new Date(Date.now() - 120000),
  },
  {
    id: '2',
    type: 'user',
    content: 'Summarize the key risks for the Acme Corp renewal',
    timestamp: new Date(Date.now() - 60000),
  },
  {
    id: '3',
    type: 'ai',
    content: `**Account Executive View:**
Single point of contact (John Smith) - no established relationships with CFO or other decision makers. Risk if John leaves.

**VP Sales View:**
$2.1M ARR renewal, 60 days out. Deal is not progressing - last activity 3 weeks ago. Recommend immediate executive business review.

**Data Analysis:**
Engagement dropped 34% over past 60 days. Competitor activity detected on LinkedIn. Win probability: 62%.

**Recommended Actions:**
1. Schedule executive business review this week
2. Expand stakeholder relationships
3. Prepare ROI justification deck`,
    timestamp: new Date(),
  },
]

export function AICopilotPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Simulate AI response
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content:
          'I&apos;m analyzing your request... In a real implementation, this would connect to the APEX AI engine for account intelligence, risk scoring, and predictive insights based on your CRM data.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiMessage])
      setIsLoading(false)
    }, 1000)
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
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed right-0 top-0 h-screen w-full md:w-96 bg-card border-l border-border flex flex-col z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-foreground">APEX Copilot</h2>
                  <p className="text-xs text-muted-foreground">AI Account Intelligence</p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="p-2 hover:bg-input rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-foreground" />
              </motion.button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask about this account..."
                  className="flex-1 bg-input border border-border rounded-lg px-3 py-2 text-sm placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleSend}
                  disabled={isLoading}
                  className="p-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  <Send className="w-4 h-4" />
                </motion.button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
