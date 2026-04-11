'use client';

import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import { Database, ShieldCheck, Zap, Globe, Lock, Sliders, Cpu, Bell, User } from 'lucide-react';
import PortfolioLedger from './PortfolioLedger';
import PipelineView from './PipelineView';
import ChatTerminal from './ChatTerminal';
import KPIGrid from './KPIGrid';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState('Portfolio');
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8001/api/accounts')
      .then(res => res.json())
      .then(data => {
        setAccounts(data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case 'Portfolio':
        return children;
      case 'Accounts':
        return (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <h2 className="text-xl font-black text-foreground uppercase tracking-[0.2em] flex items-center gap-3">
              <Database className="w-5 h-5 text-primary" />
              Accounts Ledger
            </h2>
            <PortfolioLedger 
              accounts={accounts} 
              loading={loading} 
              search="" 
              onSearchChange={() => {}} 
              onAccountClick={() => {}} 
            />
          </div>
        );
      case 'Pipeline':
        return (
          <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <h2 className="text-xl font-black text-foreground uppercase tracking-[0.2em] flex items-center gap-3">
              <Zap className="w-5 h-5 text-primary" />
              Pipeline Velocity
            </h2>
            <PipelineView />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
               <div className="glass-card p-8 border-primary/10">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-4">Pipeline Distribution</h4>
                  <div className="aspect-video bg-white/5 rounded-lg flex items-center justify-center italic text-[10px] text-muted-foreground/30">
                     [Advanced Stage Analytics Active]
                  </div>
               </div>
               <div className="glass-card p-8 border-primary/10">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-4">Quartile Forecasting</h4>
                  <div className="aspect-video bg-white/5 rounded-lg flex items-center justify-center italic text-[10px] text-muted-foreground/30">
                     [Financial Projection Core Engaged]
                  </div>
               </div>
            </div>
          </div>
        );
      case 'Intelligence':
        return (
          <div className="h-[80vh] animate-in fade-in zoom-in-95 duration-500">
             <ChatTerminal />
          </div>
        );
      case 'Strategy':
        return (
           <div className="max-w-4xl mx-auto py-20 text-center space-y-10 animate-in fade-in duration-1000">
              <div className="inline-flex p-4 bg-primary/10 rounded-full border border-primary/20 mb-4">
                 <Globe className="w-12 h-12 text-primary animate-spin-slow" />
              </div>
              <div className="space-y-4">
                 <h2 className="text-4xl font-black text-foreground uppercase tracking-[0.4em]">Strategic Core</h2>
                 <p className="text-muted-foreground font-bold max-w-lg mx-auto">
                    The APEX Strategic Engine is currently synthesizing cross-territory data to generate your Q4 Market Expansion roadmap.
                 </p>
              </div>
              <div className="grid grid-cols-3 gap-6 max-w-2xl mx-auto pt-10">
                 {[1, 2, 3].map(i => (
                    <div key={i} className="h-1 bg-white/5 rounded-full overflow-hidden">
                       <div className="h-full bg-primary/40 w-1/3 animate-loading-bar" />
                    </div>
                 ))}
              </div>
              <p className="text-[10px] font-black text-primary/40 uppercase tracking-widest animate-pulse">Neural Pathfinding in progress...</p>
           </div>
        );
      case 'Settings':
        return (
           <div className="max-w-5xl mx-auto space-y-12 animate-in fade-in slide-in-from-right-4 duration-700">
              <h2 className="text-2xl font-black text-foreground uppercase tracking-[0.3em] flex items-center gap-4">
                 <Sliders className="w-6 h-6 text-primary" />
                 Control Center
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <div className="glass-card p-10 border-white/5 space-y-6">
                    <div className="flex items-center gap-4 text-primary">
                       <Cpu className="w-5 h-5" />
                       <h4 className="text-xs font-black uppercase tracking-widest">Model Configuration</h4>
                    </div>
                    <div className="space-y-4">
                       <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/5">
                          <span className="text-[10px] font-bold text-muted-foreground">Ollama Endpoint</span>
                          <span className="text-[10px] font-black text-emerald-500">ACTIVE: 8000</span>
                       </div>
                       <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/5 opacity-50">
                          <span className="text-[10px] font-bold text-muted-foreground">Claude-3 Integration</span>
                          <span className="text-[10px] font-black text-muted-foreground">LOCKED</span>
                       </div>
                    </div>
                 </div>
                 <div className="glass-card p-10 border-white/5 space-y-6">
                    <div className="flex items-center gap-4 text-primary">
                       <Lock className="w-5 h-5" />
                       <h4 className="text-xs font-black uppercase tracking-widest">Security Ledger</h4>
                    </div>
                    <div className="space-y-4">
                       <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/5">
                          <span className="text-[10px] font-bold text-muted-foreground">Data Encryption</span>
                          <span className="text-[10px] font-black text-blue-500 uppercase">AES-256</span>
                       </div>
                       <div className="flex justify-between items-center p-4 bg-white/5 rounded-xl border border-white/5">
                          <span className="text-[10px] font-bold text-muted-foreground">Access Level</span>
                          <span className="text-[10px] font-black text-amber-500 uppercase italic">Admin Priority</span>
                       </div>
                    </div>
                 </div>
              </div>
           </div>
        );
      default:
        return children;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Persistent Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top Bar */}
        <header className="h-16 border-b border-white/5 bg-card/30 backdrop-blur-xl flex items-center justify-between px-8 shrink-0 z-50">
          <div className="flex items-center gap-4 text-xs font-black uppercase tracking-widest text-muted-foreground">
            <span 
              onClick={() => setActiveTab('Portfolio')}
              className="hover:text-primary cursor-pointer transition-colors"
            >
              Global Console
            </span>
            <span className="opacity-20">/</span>
            <span className="text-foreground">{activeTab} Ledger</span>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/5 border border-emerald-500/10 rounded-full">
               <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
               <span className="text-[9px] font-black uppercase text-emerald-500 tracking-widest">System Active</span>
            </div>
            <div className="flex items-center gap-4">
              <button className="p-2 text-muted-foreground hover:text-foreground transition-colors relative">
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-primary rounded-full border border-card"></span>
              </button>
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center group cursor-pointer hover:border-primary/50 transition-all">
                <User className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
            </div>
          </div>
        </header>

        {/* Content Scroll Area */}
        <div className="flex-1 overflow-y-auto p-8 relative scroll-smooth scrollbar-hide">
          <div className="max-w-[1500px] mx-auto uppercase">
            {renderContent()}
          </div>
        </div>
      </main>
    </div>
  );
}
