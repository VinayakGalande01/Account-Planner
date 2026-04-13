'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Bot, User, Terminal, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content?: string;
  type?: 'text' | 'structured';
  data?: any;
}

type ProcessingStage = 'idle' | 'analyzing' | 'fetching' | 'inferring' | 'complete';

const stageConfig: Record<ProcessingStage, { label: string; className: string }> = {
  idle: { label: '', className: '' },
  analyzing: { label: 'SYSTEM: ANALYZING', className: 'text-blue-400 glow-cobalt' },
  fetching: { label: 'DATA: FETCHING', className: 'text-violet-400 glow-violet' },
  inferring: { label: 'MODEL: INFERRING', className: 'text-amber-400 glow-amber' },
  complete: { label: 'COMPLETE', className: 'text-emerald-400 glow-emerald' },
};

export default function ChatTerminal({ externalCommand }: { externalCommand?: string }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      type: 'text',
      content: 'APEX v2.1 initialized. Portfolio loaded. Awaiting directive.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [processingStage, setProcessingStage] = useState<ProcessingStage>('idle');
  const [displayedResponse, setDisplayedResponse] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stageTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (externalCommand) {
      handleSend(externalCommand);
    }
  }, [externalCommand]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping, displayedResponse]);

  // Staggered text reveal effect
  const animateTextReveal = useCallback((fullText: string, onComplete: () => void) => {
    const maxAnimChars = 200;
    const charsToAnimate = Math.min(fullText.length, maxAnimChars);
    let current = 0;

    setDisplayedResponse('');

    const timer = setInterval(() => {
      current += 1;
      if (current >= charsToAnimate) {
        setDisplayedResponse(fullText);
        clearInterval(timer);
        onComplete();
      } else {
        setDisplayedResponse(fullText.substring(0, current));
      }
    }, 12);

    return () => clearInterval(timer);
  }, []);

  // Rotate through processing stages
  const startProcessingStages = useCallback(() => {
    setProcessingStage('analyzing');
    stageTimerRef.current = setTimeout(() => {
      setProcessingStage('fetching');
      stageTimerRef.current = setTimeout(() => {
        setProcessingStage('inferring');
      }, 1500);
    }, 1200);
  }, []);

  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { role: 'user', content: textToSend, type: 'text' };
    setMessages((prev) => [...prev, userMsg]);
    if (!overrideInput) setInput('');
    setIsTyping(true);
    setDisplayedResponse(null);
    startProcessingStages();

    try {
      const response = await fetch('http://localhost:8001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend }),
      });
      const result = await response.json();

      // Clear stage timers
      if (stageTimerRef.current) clearTimeout(stageTimerRef.current);
      setProcessingStage('complete');

      const fullText = result.response || '';

      // Animate reveal, then finalize
      animateTextReveal(fullText, () => {
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              type: result.type || 'text',
              content: fullText,
              data: result.data,
            },
          ]);
          setDisplayedResponse(null);
          setIsTyping(false);
          setProcessingStage('idle');
        }, 300);
      });
    } catch {
      if (stageTimerRef.current) clearTimeout(stageTimerRef.current);
      setProcessingStage('idle');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          type: 'text',
          content: 'ERR: Connection to intelligence engine failed. Verify backend status.',
        },
      ]);
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#030303] border border-white/[0.04] rounded-md overflow-hidden relative terminal-scanlines">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.04] bg-white/[0.01] flex items-center justify-between shrink-0 relative z-10">
        <div className="flex items-center gap-3">
          <Terminal className="w-3.5 h-3.5 text-primary" />
          <span className="text-[10px] font-black uppercase tracking-[0.15em] text-foreground font-[family-name:var(--font-mono)]">
            APEX v2.1
          </span>
          <span className="text-[9px] text-zinc-600 font-[family-name:var(--font-mono)]">// SESSION ACTIVE</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        </div>
      </div>

      {/* Processing Stage Indicator */}
      <AnimatePresence>
        {processingStage !== 'idle' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 py-2 border-b border-white/[0.04] bg-white/[0.01] relative z-10"
          >
            <span className={`inline-flex items-center gap-2 px-2.5 py-1 rounded text-[9px] font-black uppercase tracking-[0.12em] font-[family-name:var(--font-mono)] border border-white/[0.06] ${stageConfig[processingStage].className}`}>
              <div className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              {stageConfig[processingStage].label}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scroll-smooth scrollbar-tactical relative z-10">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-6 h-6 rounded bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3 h-3 text-primary" />
              </div>
            )}

            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              {msg.role === 'user' ? (
                <div className="px-3 py-2 rounded-md bg-primary/10 border border-primary/20 text-[11px] font-bold text-foreground font-[family-name:var(--font-mono)]">
                  <span className="text-primary mr-2">&gt;</span>
                  {msg.content}
                </div>
              ) : (
                <div className="text-[11px] text-zinc-300 leading-relaxed whitespace-pre-wrap font-[family-name:var(--font-mono)]">
                  {msg.content}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-6 h-6 rounded bg-white/[0.04] flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3 h-3 text-zinc-500" />
              </div>
            )}
          </div>
        ))}

        {/* Typing / Reveal State */}
        {isTyping && (
          <div className="flex gap-3">
            <div className="w-6 h-6 rounded bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
              <Bot className="w-3 h-3 text-primary" />
            </div>
            <div className="text-[11px] text-zinc-300 leading-relaxed whitespace-pre-wrap font-[family-name:var(--font-mono)] max-w-[85%]">
              {displayedResponse !== null ? (
                <>
                  {displayedResponse}
                  <span className="inline-block w-2 h-4 bg-primary ml-0.5 animate-blink-cursor align-middle" />
                </>
              ) : (
                <span className="inline-block w-2 h-4 bg-primary animate-blink-cursor" />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-white/[0.04] bg-white/[0.01] relative z-10">
        <div className="flex items-center gap-2">
          <span className="text-primary text-[11px] font-[family-name:var(--font-mono)] font-bold shrink-0">&gt;_</span>
          <input
            type="text"
            placeholder="Query account intelligence..."
            className="flex-1 bg-transparent text-[11px] text-foreground placeholder:text-zinc-700 focus:outline-none font-[family-name:var(--font-mono)] font-medium"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            onClick={() => handleSend()}
            disabled={isTyping || !input.trim()}
            className="p-1.5 text-primary hover:bg-primary/10 rounded transition-all disabled:opacity-20"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
