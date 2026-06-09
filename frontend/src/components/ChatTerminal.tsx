'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Terminal, Bot, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';
import { parseResponseContract } from '../utils/contractParser';

import { ContractRenderer, FinalizedContractRenderer } from './apex-widgets';
import type { ResponseContract } from '../types/responseContract';

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

const stageConfig: Record<string, { label: string; className: string }> = {
  idle: { label: '', className: '' },
  running: { label: 'THINKING...', className: 'text-amber-500 border-amber-500/20 bg-amber-500/10' },
  complete: { label: 'FINISHED!', className: 'text-emerald-500 border-emerald-500/20 bg-emerald-500/10' },
};

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
      const response = await authFetch('http://127.0.0.1:8002/api/chat', {
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
        // Normalize streamed content into structured ResponseContract
        // __SECTION_*__ is strictly a transport format — we normalize to application state here
        const contract = parseResponseContract(accumulateStr);

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            type: 'text',
            content: accumulateStr.trim(),
            contract: contract.isStructured ? contract : undefined,
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
      return <FinalizedContractRenderer contract={msg.contract} />;
    }
    return (
      <div className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-mono)]">
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
    if (displayedResponse === null) {
      return <span className="inline-block w-2 h-4 bg-primary animate-blink-cursor" />;
    }

    // Check if the stream contains structured __SECTION_*__ tags
    const hasStructuredContent = displayedResponse.includes('__SECTION_');

    if (hasStructuredContent) {
      return <ContractRenderer content={displayedResponse} isStreaming={true} />;
    }

    // Fallback: render as raw text with cursor
    return (
      <>
        <RenderMessageLines content={displayedResponse} />
        <span className="inline-block w-2 h-4 bg-primary ml-0.5 animate-blink-cursor align-middle" />
      </>
    );
  };

  return (
    <div className="corner-brackets flex flex-col h-full bg-background rounded-md overflow-hidden relative">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0 relative z-10">
        <div className="flex items-center gap-3">
          <Terminal className="w-3.5 h-3.5 text-primary" />
          <span className="text-[13px] font-black uppercase tracking-[0.15em] text-foreground font-[family-name:var(--font-mono)]">
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

      {/* Processing Stage Indicator */}
      <AnimatePresence>
        {processingStage !== 'idle' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 py-2 border-b border-border bg-muted/30 relative z-10"
          >
            <span className={`inline-flex items-center gap-2 px-2.5 py-1 rounded text-[12px] font-black uppercase tracking-[0.12em] font-[family-name:var(--font-mono)] border border-border ${stageConfig[processingStage].className}`}>
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
                <div className="px-3 py-2 rounded-md bg-primary/10 border border-primary/20 text-sm font-bold text-foreground font-[family-name:var(--font-mono)]">
                  <span className="text-primary mr-2">&gt;</span>
                  {msg.content}
                </div>
              ) : (
                renderAssistantMessage(msg)
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-6 h-6 rounded bg-muted flex items-center justify-center shrink-0 mt-0.5">
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
            <div className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-mono)] max-w-[85%]">
              {renderStreamingResponse()}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 pb-4 pt-2 bg-transparent relative z-10 shrink-0">
        <div className="chatbox-glow-ring p-3 flex items-center gap-2">
          <span className="text-primary text-sm font-[family-name:var(--font-mono)] font-bold shrink-0">&gt;_</span>
          <input
            type="text"
            placeholder="Ask a question about your accounts..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-zinc-500 focus:outline-none font-[family-name:var(--font-mono)] font-medium"
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
