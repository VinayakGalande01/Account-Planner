'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Terminal, CheckCircle2, AlertTriangle, ShieldCheck, Target, TrendingUp, Zap, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content?: string;
  type?: 'text' | 'structured';
  data?: any;
}

export default function ChatTerminal({ externalCommand }: { externalCommand?: string }) {
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'assistant', 
      type: 'text', 
      content: 'Welcome, Strategic Advisor. I have analyzed your portfolio. Which account shall we deep-dive into today?' 
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (externalCommand) {
      handleSend(externalCommand);
    }
  }, [externalCommand]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) return;

    const userMsg: Message = { role: 'user', content: textToSend, type: 'text' };
    setMessages(prev => [...prev, userMsg]);
    if (!overrideInput) setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:8001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend }),
      });
      const result = await response.json();
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        type: result.type || 'text',
        content: result.response,
        data: result.data
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        type: 'text',
        content: 'Error connecting to intelligence engine. Ensure backend is running.' 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="glass-card flex flex-col h-[700px] border-primary/20 bg-primary/5 overflow-hidden shadow-2xl relative">
      {/* Header */}
      <div className="p-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/20 rounded-xl">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-foreground">Strategic Intelligence</h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
              <span className="text-[10px] font-bold text-muted-foreground uppercase">Live Analysis</span>
            </div>
          </div>
        </div>
        <Sparkles className="w-4 h-4 text-primary/40" />
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth scrollbar-hide">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 15, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div className={`p-2 rounded-xl h-fit shrink-0 ${msg.role === 'user' ? 'bg-primary/20' : 'bg-white/10'}`}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-primary" /> : <Bot className="w-4 h-4 text-primary" />}
              </div>
              
              <div className={`max-w-[85%] space-y-4`}>
                {msg.type === 'structured' && msg.data ? (
                  <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
                    {/* Summary Section */}
                    <div className="bg-white/5 border border-white/10 p-5 rounded-2xl relative overflow-hidden group">
                      <div className="absolute top-0 left-0 w-1 h-full bg-primary/50" />
                      <p className="text-sm font-medium leading-relaxed text-foreground/90 italic">"{msg.data.summary}"</p>
                    </div>

                    {/* Actions Section */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between px-1">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-primary flex items-center gap-2">
                          <Target className="w-3 h-3" />
                          Prioritized Actions
                        </h4>
                        <span className="text-[9px] font-black text-muted-foreground/40 italic">STRATEGIC PRIORITY</span>
                      </div>
                      <div className="grid grid-cols-1 gap-3">
                        {msg.data.actions?.map((action: any, idx: number) => (
                          <div key={idx} className="bg-white/5 border border-white/5 p-4 rounded-xl flex items-center gap-4 hover:border-primary/40 hover:bg-white/10 transition-all cursor-pointer group shadow-sm">
                            <div className="bg-emerald-500/20 p-2 rounded-lg group-hover:bg-emerald-500/30 transition-colors">
                              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-black text-foreground truncate">{action.name}</p>
                              <div className="flex items-center gap-3 mt-1.5">
                                <span className="text-[9px] px-1.5 py-0.5 bg-primary/10 text-primary font-black rounded">{action.priority}</span>
                                <span className="text-[9px] text-muted-foreground flex items-center gap-1 uppercase">
                                  <User className="w-2.5 h-2.5" /> {action.owner}
                                </span>
                              </div>
                            </div>
                            <div className="text-right shrink-0">
                              <p className="text-[10px] font-bold text-muted-foreground">{action.due_date}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Risks & Advantages Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-rose-500 flex items-center gap-2 px-1">
                          <AlertTriangle className="w-3 h-3" />
                          Key Risks
                        </h4>
                        {msg.data.risks?.map((risk: any, idx: number) => (
                          <div key={idx} className="bg-rose-500/5 border border-rose-500/10 p-3 rounded-xl">
                            <p className="text-xs font-bold text-foreground mb-1">{risk.title}</p>
                            <p className="text-[10px] text-muted-foreground leading-relaxed italic">{risk.mitigation}</p>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-secondary flex items-center gap-2 px-1">
                          <TrendingUp className="w-3 h-3" />
                          Advantages
                        </h4>
                        <div className="space-y-2">
                          {msg.data.advantages?.map((adv: string, idx: number) => (
                            <div key={idx} className="bg-secondary/5 border border-secondary/10 px-3 py-2 rounded-lg flex items-center gap-2">
                              <Zap className="w-2.5 h-2.5 text-secondary" />
                              <span className="text-[10px] font-bold text-foreground/80">{adv}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className={`p-4 rounded-2xl text-sm shadow-xl leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground font-black rounded-tr-none border-b-2 border-black/10' 
                      : 'bg-white/5 border border-white/10 text-foreground/90 rounded-tl-none font-medium'
                  }`}>
                    {msg.content}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isTyping && (
          <div className="flex gap-4">
            <div className="p-2 rounded-xl bg-white/10 h-fit">
              <Bot className="w-4 h-4 text-primary animate-pulse" />
            </div>
            <div className="bg-white/5 border border-white/10 p-5 rounded-2xl rounded-tl-none shadow-inner">
              <div className="flex gap-2">
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce delay-150"></span>
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce delay-300"></span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Section */}
      <div className="p-6 bg-white/5 border-t border-white/5 relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 px-4 py-1 bg-background border border-white/5 rounded-full text-[8px] font-black tracking-widest text-muted-foreground uppercase">
          Neural Interface Active
        </div>
        <div className="relative">
          <input 
            type="text" 
            placeholder="Query account intelligence..."
            className="w-full bg-muted/30 border border-white/10 rounded-2xl pl-5 pr-14 py-4 focus:outline-none focus:ring-2 focus:ring-primary/20 text-sm text-foreground placeholder:text-muted-foreground/30 transition-all font-bold shadow-inner"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button 
            onClick={() => handleSend()}
            disabled={isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 text-primary hover:bg-primary/20 rounded-xl transition-all disabled:opacity-30 flex items-center gap-2 group"
          >
            <Send className="w-5 h-5 group-hover:translate-x-1 group-active:scale-90 transition-all" />
          </button>
        </div>
      </div>
    </div>
  );
}
