'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Terminal, Bot, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type MessageType = 'text' | 'data' | 'system';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  type: MessageType;
  data?: any;
}

const initialMessages: Message[] = [
  {
    role: 'assistant',
    type: 'text',
    content: 'APEX v2.1 initialized. Portfolio loaded.\nAwaiting directive.',
  },
];

const stageConfig: Record<string, { label: string; className: string }> = {
  idle: { label: '', className: '' },
  running: { label: 'PROCESSING NEURAL INFERENCE', className: 'text-amber-500 border-amber-500/20 bg-amber-500/10' },
  complete: { label: 'INFERENCE COMPLETE', className: 'text-emerald-500 border-emerald-500/20 bg-emerald-500/10' },
};

function RenderMessageLines({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <>
      {lines.map((line, idx) => {
        if (line.startsWith('sys_meta_log|')) {
          const metaMsg = line.replace('sys_meta_log|', '');
          return (
            <div key={idx} className="text-[9px] text-zinc-600 font-bold tracking-widest my-1 uppercase">
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

export default function ChatTerminal({ externalCommand }: { externalCommand?: string | null }) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedResponse, setDisplayedResponse] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<'idle' | 'running' | 'complete'>('idle');

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo(0, scrollRef.current.scrollHeight);
    }
  }, [messages, displayedResponse, processingStage, isTyping]);

  useEffect(() => {
    if (externalCommand) {
      handleSend(externalCommand);
    }
  }, [externalCommand]);

  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { role: 'user', content: textToSend, type: 'text' };
    setMessages((prev) => [...prev, userMsg]);
    if (!overrideInput) setInput('');
    setIsTyping(true);
    setDisplayedResponse('');
    setProcessingStage('running');

    try {
      const response = await fetch('http://localhost:8001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend }),
      });

      if (!response.body) throw new Error('No stream body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulateStr = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulateStr += chunk;
        setDisplayedResponse(accumulateStr);
      }

      setProcessingStage('complete');
      
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            type: 'text',
            content: accumulateStr.trim(),
          },
        ]);
        setDisplayedResponse(null);
        setIsTyping(false);
        setProcessingStage('idle');
      }, 500);

    } catch (err) {
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
      setDisplayedResponse(null);
    }
  };

  return (
    <div className="corner-brackets flex flex-col h-full bg-[#030303] rounded-md overflow-hidden relative">
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
          <div className="flex items-center space-x-[2px] h-2">
            <div className="w-[1px] h-full bg-emerald-500 pulse-waveform" style={{ animationDelay: '0ms' }} />
            <div className="w-[1px] h-full bg-emerald-500 pulse-waveform" style={{ animationDelay: '150ms' }} />
          </div>
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
                <div className="text-[11px] text-zinc-300 leading-relaxed font-[family-name:var(--font-mono)]">
                  <RenderMessageLines content={msg.content} />
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
            <div className="text-[11px] text-zinc-300 leading-relaxed font-[family-name:var(--font-mono)] max-w-[85%]">
              {displayedResponse !== null ? (
                <>
                  <RenderMessageLines content={displayedResponse} />
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
