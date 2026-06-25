'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/Sidebar'
import { Header } from '@/components/header'
import { Brain, Send, Zap } from 'lucide-react'
import { ContractRenderer, FinalizedContractRenderer } from '@/components/apex-widgets'
import { parseResponseContract } from '@/utils/contractParser'
import type { ResponseContract, RecommendedAction } from '@/types/responseContract'

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  contract?: ResponseContract;
}

function RenderMessageLines({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <>
      {lines.map((line, idx) => {
        if (line.startsWith('sys_meta_log|')) {
          const metaMsg = line.replace('sys_meta_log|', '')
          return (
            <div key={idx} className="text-[12px] text-zinc-600 font-bold tracking-widest my-1 uppercase">
              {metaMsg}
            </div>
          )
        }
        return (
          <div key={idx} className={idx === lines.length - 1 ? "new-stream-line min-h-[16px]" : "min-h-[16px]"}>
            {line}
          </div>
        )
      })}
    </>
  )
}

const initialMessages: Message[] = [
  {
    id: 1,
    role: 'assistant',
    content: 'APEX is ready. Client list loaded. How can I help you today?',
    timestamp: new Date(Date.now() - 5 * 60000),
  },
]

const suggestedPrompts = [
  'Show me accounts at high risk',
  'Which accounts have the most potential?',
  'Analyze sales velocity trends',
  'Recommend next actions for top accounts',
]

export default function IntelligencePage() {
  const { authFetch } = useAuth()
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mounted, setMounted] = useState(false)

  const handleActionClick = (action: RecommendedAction) => {
    if (!isLoading) {
      handleSendMessage(action.title)
    }
  }

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleSendMessage = async (text = inputValue) => {
    if (!text.trim() || isLoading) return

    // Add user message
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await authFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      })

      if (!response.body) throw new Error('No stream body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullText = ''
      
      const aiMessageId = Date.now() + 1
      setMessages((prev) => [...prev, { id: aiMessageId, role: 'assistant', content: '', timestamp: new Date() }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        fullText += chunk
        
        setMessages((prev) => prev.map(msg => msg.id === aiMessageId ? { ...msg, content: fullText } : msg))
      }

      const contract = parseResponseContract(fullText)
      setMessages((prev) => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: fullText, contract: contract.isStructured ? contract : undefined } 
          : msg
      ))
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
    <div className="flex h-screen bg-background">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Header />

        <main className="flex-1 overflow-y-auto flex flex-col">
          <div className="flex-1 p-6 md:p-8 flex flex-col">
            {/* Page title */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-6"
            >
              <div className="flex items-center gap-2">
                <Brain className="w-6 h-6 text-primary" />
                <h1 className="text-3xl font-semibold text-foreground">Intelligence</h1>
              </div>
              <p className="text-sm text-muted-foreground mt-1">APEX V2.1 - Connected | Ask me anything about your accounts</p>
            </motion.div>

            {/* Messages */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="flex-1 bg-card border border-border rounded-lg p-5 mb-4 overflow-y-auto"
            >
              <div className="space-y-4 flex flex-col">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <Brain className="w-12 h-12 text-primary/30 mx-auto mb-3" />
                      <p className="text-muted-foreground">Start a conversation...</p>
                    </div>
                  </div>
                ) : (
                  messages.map((message, index) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`px-4 py-2 rounded-lg ${
                          message.role === 'user'
                            ? 'max-w-lg bg-primary text-primary-foreground'
                            : 'max-w-3xl bg-secondary/50 text-foreground border border-border w-full'
                        }`}
                      >
                        {message.role === 'assistant' ? (
                          message.contract ? (
                            <FinalizedContractRenderer contract={message.contract} onActionClick={handleActionClick} />
                          ) : message.content.includes('__SECTION_') ? (
                            <ContractRenderer content={message.content} isStreaming={isLoading && index === messages.length - 1} onActionClick={handleActionClick} />
                          ) : (
                            <div className="text-sm leading-relaxed">
                              <RenderMessageLines content={message.content} />
                              {isLoading && index === messages.length - 1 && (
                                <span className="inline-block w-[2px] h-4 bg-primary ml-0.5 animate-pulse align-middle rounded-full" />
                              )}
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
                  ))
                )}

                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-3"
                  >
                    <div className="bg-secondary/50 text-foreground border border-border px-4 py-2 rounded-lg">
                      <div className="flex gap-1.5">
                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse" />
                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse delay-100" />
                        <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse delay-200" />
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>

            {/* Suggested prompts (only show initially) */}
            {messages.length === 1 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.4 }}
                className="mb-4"
              >
                <p className="text-xs text-muted-foreground mb-2">Suggested questions:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {suggestedPrompts.map((prompt, index) => (
                    <motion.button
                      key={prompt}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.25 + index * 0.05 }}
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
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4 }}
              className="flex gap-3"
            >
              <input
                type="text"
                placeholder="Ask a question about your accounts..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                disabled={isLoading}
                className="flex-1 bg-secondary border border-border rounded-lg px-4 py-2.5 text-sm placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors disabled:opacity-50"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={isLoading || !inputValue.trim()}
                className="px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  )
}
