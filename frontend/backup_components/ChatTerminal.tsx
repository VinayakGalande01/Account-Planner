'use client';

// LEGACY/BACKUP FILE — not part of the active build (frontend/src is the live app).
// Original AI chat/intelligence terminal: streams responses from /api/chat via a
// ReadableStream, reveals them with a typewriter effect, parses structured
// "__SECTION_*__" response contracts into rich widgets, and offers a prompt library.
//
// --- SECTION: Types & Initial Messages ---
// --- SECTION: ThinkingIndicator (stage animation) & RenderMessageLines (fallback text) ---
// --- SECTION: ChatTerminal Component — state, prompt fetch, typewriter engine ---
// --- SECTION: handleSend — streams/reads chat response, builds message contract ---
// --- SECTION: Render — Header, Thinking Indicator, Message List ---
// --- SECTION: Render — Prompt Library Popover & Input Bar ---

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Sparkles, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';
import { parseResponseContract } from '../utils/contractParser';

import { ContractRenderer, FinalizedContractRenderer } from './apex-widgets';
import type { ResponseContract, RecommendedAction } from '../types/responseContract';

type MessageType = 'text' | 'data' | 'system';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  type: MessageType;
  data?: any;
  /** Normalized structured response contract (post-stream application state) */
  contract?: ResponseContract;
}

const initialMessages: Message[] = [
  {
    role: 'assistant',
    type: 'text',
    content: 'APEX is ready. Client list loaded.\nHow can I help you today?',
  },
];

/**
 * Thinking animation — ChatGPT-style animated dots with contextual stage messages.
 */
function ThinkingIndicator({ stage }: { stage: 'running' | 'complete' }) {
  const messages = [
    'Analyzing your query',
    'Retrieving account data',
    'Generating insights',
  ];
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    if (stage !== 'running') return;
    const timer = setInterval(() => {
      setMsgIndex((prev) => (prev + 1) % messages.length);
    }, 3000);
    return () => clearInterval(timer);
  }, [stage]);

  if (stage === 'complete') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 text-emerald-400 text-[12px] font-[family-name:var(--font-inter)] font-medium"
      >
        <Sparkles className="w-3 h-3" />
        <span>Response ready</span>
      </motion.div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {/* Animated bouncing dots */}
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-primary"
            animate={{
              scale: [1, 1.4, 1],
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 1,
              repeat: Infinity,
              delay: i * 0.2,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      {/* Contextual stage message with crossfade */}
      <AnimatePresence mode="wait">
        <motion.span
          key={msgIndex}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.3 }}
          className="text-[12px] text-zinc-500 font-[family-name:var(--font-inter)]"
        >
          {messages[msgIndex]}...
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

/**
 * Fallback renderer for unstructured text content.
 * Used for: welcome messages, error messages, and responses without __SECTION_*__ tags.
 */
function RenderMessageLines({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <>
      {lines.map((line, idx) => {
        if (line.startsWith('sys_meta_log|')) {
          const metaMsg = line.replace('sys_meta_log|', '');
          return (
            <div key={idx} className="text-[12px] text-zinc-600 font-bold tracking-widest my-1 uppercase">
              {metaMsg}
            </div>
          );
        }
        return (
          <div key={idx} className={idx === lines.length - 1 ? "new-stream-line min-h-[16px]" : "min-h-[16px]"}>
            {line}
          </div>
        );
      })}
    </>
  );
}

export default function ChatTerminal() {
  const { aiCommand, setAiCommand } = useData();
  const { authFetch } = useAuth();

  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedResponse, setDisplayedResponse] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<'idle' | 'running' | 'complete'>('idle');

  // Prompt Library states
  const [showPromptLibrary, setShowPromptLibrary] = useState(false);
  const [libraryPrompts, setLibraryPrompts] = useState<any[]>([]);

  // Typewriter state
  const fullResponseRef = useRef<string>('');
  const typewriterTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const revealIndexRef = useRef<number>(0);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight);
    }
  }, [messages, displayedResponse, processingStage, isTyping]);

  useEffect(() => {
    if (aiCommand) {
      handleSend(aiCommand);
      setAiCommand(undefined); // Clear after triggering
    }
  }, [aiCommand, setAiCommand]);

  // Cleanup typewriter timer on unmount
  useEffect(() => {
    return () => {
      if (typewriterTimerRef.current) {
        clearInterval(typewriterTimerRef.current);
      }
    };
  }, []);

  // Fetch prompts list on mount
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        const response = await authFetch('/api/prompts');
        if (response.ok) {
          const data = await response.json();
          setLibraryPrompts(data);
        }
      } catch (err) {
        console.error('Failed to fetch prompts', err);
      }
    };
    fetchPrompts();
  }, [authFetch]);

  /**
   * Typewriter reveal — smoothly reveals characters from the buffer.
   * Runs at ~20ms per character for a ChatGPT-like streaming feel.
   * Catches up faster if buffer is far ahead (prevents lag).
   */
  const startTypewriter = useCallback(() => {
    if (typewriterTimerRef.current) return; // Already running

    typewriterTimerRef.current = setInterval(() => {
      const fullText = fullResponseRef.current;
      const currentIdx = revealIndexRef.current;

      if (currentIdx >= fullText.length) {
        // Nothing new to reveal yet — wait for more stream data
        return;
      }

      // Reveal characters in chunks for speed — larger chunks when far behind
      const gap = fullText.length - currentIdx;
      const chunkSize = gap > 200 ? Math.min(gap, 40) : gap > 50 ? 8 : 2;
      const newIdx = Math.min(currentIdx + chunkSize, fullText.length);

      revealIndexRef.current = newIdx;
      setDisplayedResponse(fullText.slice(0, newIdx));
    }, 18);
  }, []);

  const stopTypewriter = useCallback(() => {
    if (typewriterTimerRef.current) {
      clearInterval(typewriterTimerRef.current);
      typewriterTimerRef.current = null;
    }
  }, []);


  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { role: 'user', content: textToSend, type: 'text' };
    setMessages((prev) => [...prev, userMsg]);
    if (!overrideInput) setInput('');
    setIsTyping(true);
    setDisplayedResponse('');
    setProcessingStage('running');

    // Reset typewriter state
    fullResponseRef.current = '';
    revealIndexRef.current = 0;

    try {
      const response = await authFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend }),
      });

      if (!response.body) throw new Error('No stream body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      // Start typewriter reveal
      startTypewriter();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullResponseRef.current += chunk;
      }

      // Stream complete — flush remaining characters quickly
      const flushRemaining = () => {
        const fullText = fullResponseRef.current;
        if (revealIndexRef.current < fullText.length) {
          const gap = fullText.length - revealIndexRef.current;
          const chunkSize = Math.max(Math.floor(gap / 5), 10);
          revealIndexRef.current = Math.min(revealIndexRef.current + chunkSize, fullText.length);
          setDisplayedResponse(fullText.slice(0, revealIndexRef.current));

          if (revealIndexRef.current < fullText.length) {
            requestAnimationFrame(flushRemaining);
            return;
          }
        }

        // All characters revealed — finalize
        stopTypewriter();
        setDisplayedResponse(fullText);
        setProcessingStage('complete');

        setTimeout(() => {
          const contract = parseResponseContract(fullText);
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              type: 'text',
              content: fullText.trim(),
              contract: contract.isStructured ? contract : undefined,
            },
          ]);
          setDisplayedResponse(null);
          setIsTyping(false);
          setProcessingStage('idle');
        }, 600);
      };

      stopTypewriter();
      flushRemaining();

    } catch (err) {
      stopTypewriter();
      setProcessingStage('idle');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          type: 'text',
          content: 'Error: Could not connect to the AI. Please verify server status.',
        },
      ]);
      setIsTyping(false);
      setDisplayedResponse(null);
    }
  };

  /**
   * Renders a stored assistant message.
   * Uses FinalizedContractRenderer for structured responses,
   * falls back to RenderMessageLines for unstructured text.
   */
  const renderAssistantMessage = (msg: Message) => {
    if (msg.contract) {
      return <FinalizedContractRenderer contract={msg.contract} onActionClick={handleActionClick} />;
    }
    return (
      <div className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-inter)]">
        <RenderMessageLines content={msg.content} />
      </div>
    );
  };

  /**
   * Renders the actively-streaming response.
   * Uses ContractRenderer for structured streams (with choreography),
   * falls back to RenderMessageLines for unstructured streams.
   */
  const renderStreamingResponse = () => {
    if (displayedResponse === null || displayedResponse === '') {
      return null;
    }

    // Check if the stream contains structured __SECTION_*__ tags
    const hasStructuredContent = displayedResponse.includes('__SECTION_');

    if (hasStructuredContent) {
      return <ContractRenderer content={displayedResponse} isStreaming={true} onActionClick={handleActionClick} />;
    }

    // Fallback: render as raw text with cursor
    return (
      <>
        <RenderMessageLines content={displayedResponse} />
        <span className="inline-block w-[2px] h-4 bg-primary ml-0.5 animate-blink-cursor align-middle rounded-full" />
      </>
    );
  };

  /**
   * Handles click on a recommended action chip.
   * Sends the action's title as a new user query.
   */
  const handleActionClick = useCallback((action: RecommendedAction) => {
    if (!isTyping) {
      handleSend(action.title);
    }
  }, [isTyping]);

  return (
    <div className="corner-brackets flex flex-col h-full bg-background rounded-md overflow-hidden relative">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-primary" />
          </div>
          <span className="text-[13px] font-bold uppercase tracking-[0.12em] text-foreground font-[family-name:var(--font-mono)]">
            APEX v2.1
          </span>
          <span className="text-[12px] text-zinc-500 dark:text-zinc-600 font-[family-name:var(--font-mono)]">// CONNECTED</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center space-x-[2px] h-2">
            <div className="w-[1px] h-full bg-emerald-500 pulse-waveform" style={{ animationDelay: '0ms' }} />
            <div className="w-[1px] h-full bg-emerald-500 pulse-waveform" style={{ animationDelay: '150ms' }} />
          </div>
        </div>
      </div>

      {/* Processing Stage Indicator — ChatGPT-style thinking animation */}
      <AnimatePresence>
        {processingStage !== 'idle' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="px-4 py-2.5 border-b border-border bg-muted/20 relative z-10"
          >
            <ThinkingIndicator stage={processingStage} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5 space-y-5 scroll-smooth scrollbar-tactical relative z-10">
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={i > 0 ? { opacity: 0, y: 12 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-violet-500/20 flex items-center justify-center shrink-0 mt-0.5 border border-primary/10">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
            )}

            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              {msg.role === 'user' ? (
                <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-primary/10 border border-primary/15 text-sm font-medium text-foreground font-[family-name:var(--font-inter)]">
                  {msg.content}
                </div>
              ) : (
                renderAssistantMessage(msg)
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5 border border-border">
                <User className="w-3.5 h-3.5 text-zinc-500" />
              </div>
            )}
          </motion.div>
        ))}

        {/* Typing / Reveal State */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex gap-3"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-violet-500/20 flex items-center justify-center shrink-0 mt-0.5 border border-primary/10">
              <Bot className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-inter)] max-w-[85%]">
              {renderStreamingResponse()}
              {/* Show blinking cursor when no content yet */}
              {(displayedResponse === null || displayedResponse === '') && processingStage === 'running' && (
                <span className="inline-block w-[2px] h-4 bg-primary animate-blink-cursor rounded-full" />
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 bg-transparent relative z-10 shrink-0">
        <AnimatePresence>
          {showPromptLibrary && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="absolute bottom-16 left-4 right-4 bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl z-20 max-h-[320px] overflow-y-auto p-4 space-y-3 scrollbar-tactical mb-2"
            >
              <div className="flex justify-between items-center pb-2 border-b border-zinc-800">
                <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest font-[family-name:var(--font-mono)] flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-primary" /> Prompt Library
                </span>
                <button
                  onClick={() => setShowPromptLibrary(false)}
                  className="text-[10px] text-zinc-500 hover:text-zinc-300 uppercase font-bold tracking-wider font-[family-name:var(--font-mono)]"
                >
                  Close
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {libraryPrompts.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setInput(p.text);
                      setShowPromptLibrary(false);
                    }}
                    className="text-left p-3 rounded-lg border border-zinc-800 hover:border-primary/40 bg-zinc-900/40 hover:bg-primary/5 transition-all flex items-start gap-2.5 group cursor-pointer"
                  >
                    <span className="text-base shrink-0 select-none">{p.icon || '💬'}</span>
                    <div className="space-y-0.5">
                      <div className="text-[12.5px] font-semibold text-zinc-200 group-hover:text-primary transition-colors leading-snug">
                        {p.text}
                      </div>
                      <div className="text-[9px] font-bold uppercase tracking-wider text-zinc-600 group-hover:text-primary/50 transition-colors font-[family-name:var(--font-mono)]">
                        {p.category}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="chatbox-glow-ring p-3 flex items-center gap-2">
          <button
            onClick={() => setShowPromptLibrary((prev) => !prev)}
            className={`p-1.5 rounded transition-all cursor-pointer flex items-center justify-center shrink-0 ${
              showPromptLibrary ? 'text-primary bg-primary/10' : 'text-zinc-500 hover:text-primary hover:bg-zinc-800/40'
            }`}
            title="Prompt Library"
          >
            <BookOpen className="w-4 h-4" />
          </button>
          <span className="text-primary text-sm font-[family-name:var(--font-mono)] font-bold shrink-0">&gt;_</span>
          <input
            type="text"
            placeholder="Ask a question about your accounts..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-zinc-500 focus:outline-none font-[family-name:var(--font-inter)] font-medium"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            onClick={() => handleSend()}
            disabled={isTyping || !input.trim()}
            className="p-1.5 text-primary hover:bg-primary/10 rounded transition-all disabled:opacity-20 cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
