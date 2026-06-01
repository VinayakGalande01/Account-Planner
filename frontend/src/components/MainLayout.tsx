'use client';

import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import Sidebar from './Sidebar';
import LandingPage from './LandingPage';
import { Database, Zap, Globe, Lock, Sliders, Cpu, Bell, User, Sparkles } from 'lucide-react';
import PortfolioLedger from './PortfolioLedger';
import PipelineView from './PipelineView';
import ChatTerminal from './ChatTerminal';
import AccountDetail from './AccountDetail';
import ProactiveInsights from './ProactiveInsights';
import { useData } from '../context/DataContext';

import { motion, AnimatePresence } from 'framer-motion';


/* ── Global Loading Context ── */
interface LoadingContextType {
  isLoading: boolean;
  setLoading: (val: boolean) => void;
}
const LoadingContext = createContext<LoadingContextType>({ isLoading: false, setLoading: () => {} });
export const useGlobalLoading = () => useContext(LoadingContext);

/* ── Topographic SVG for Strategy Page ── */
function TopographicOverlay() {
  const lines = Array.from({ length: 12 }, (_, i) => {
    const cx = 200 + Math.sin(i * 1.3) * 120;
    const cy = 150 + Math.cos(i * 0.9) * 80;
    const rx = 60 + i * 18;
    const ry = 40 + i * 12;
    return { cx, cy, rx, ry, delay: i * 0.6 };
  });

  return (
    <svg className="absolute inset-0 w-full h-full topo-overlay" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      {lines.map((l, i) => (
        <ellipse
          key={i}
          cx={l.cx}
          cy={l.cy}
          rx={l.rx}
          ry={l.ry}
          fill="none"
          stroke="#2563eb"
          strokeWidth="0.3"
          opacity="0.15"
          className="topo-line"
          style={{ animationDelay: `${l.delay}s` }}
        />
      ))}
      {/* Cluster nodes */}
      {[
        { x: 120, y: 100 }, { x: 280, y: 80 }, { x: 200, y: 200 },
        { x: 320, y: 180 }, { x: 80, y: 220 }, { x: 350, y: 260 },
      ].map((n, i) => (
        <g key={i}>
          <circle cx={n.x} cy={n.y} r="2" fill="#2563eb" opacity="0.3" />
          <circle cx={n.x} cy={n.y} r="6" fill="none" stroke="#2563eb" strokeWidth="0.3" opacity="0.15" className="animate-pulse" />
        </g>
      ))}
      {/* Connection lines */}
      <line x1="120" y1="100" x2="200" y2="200" stroke="#2563eb" strokeWidth="0.2" opacity="0.1" className="topo-line" />
      <line x1="280" y1="80" x2="200" y2="200" stroke="#2563eb" strokeWidth="0.2" opacity="0.1" className="topo-line" style={{ animationDelay: '2s' }} />
      <line x1="200" y1="200" x2="320" y2="180" stroke="#2563eb" strokeWidth="0.2" opacity="0.1" className="topo-line" style={{ animationDelay: '4s' }} />
    </svg>
  );
}

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const { 
    accounts, 
    loading, 
    search, 
    activeTab, 
    setActiveTab, 
    selectedAccount, 
    setSelectedAccount 
  } = useData();
  const [consoleActive, setConsoleActive] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [insightsOpen, setInsightsOpen] = useState(false);

  const [systemStatus, setSystemStatus] = useState<'operational' | 'offline' | 'connecting'>('connecting');
  const [isLoading, setIsLoading] = useState(false);

  // Health check
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8002/api/health', { signal: AbortSignal.timeout(3000) });
      setSystemStatus(res.ok ? 'operational' : 'offline');
    } catch {
      setSystemStatus('offline');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const handleInitialize = () => {
    setConsoleActive(true);
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'Dashboard':
        return children;
      case 'Accounts':
        return (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {selectedAccount ? (
              <AccountDetail
                account={selectedAccount}
                onBack={() => setSelectedAccount(null)}
              />
            ) : (
              <>
                <h2 className="text-sm font-black text-foreground uppercase tracking-[0.4em] flex items-center gap-3 font-[family-name:var(--font-mono)]">
                  <Database className="w-3.5 h-3.5 text-primary" />
                  Account Directory
                </h2>
                <PortfolioLedger
                  accounts={accounts}
                  loading={loading}
                  search={search}
                  onSearchChange={() => {}}
                  onAccountClick={(acc) => setSelectedAccount(acc)}
                />
              </>
            )}
          </div>
        );
      case 'Pipeline':
        return (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <h2 className="text-sm font-black text-foreground uppercase tracking-[0.4em] flex items-center gap-3 font-[family-name:var(--font-mono)]">
              <Zap className="w-3.5 h-3.5 text-primary" />
              Sales Speed
            </h2>
            <PipelineView />
          </div>
        );
      case 'Intelligence':
        return (
          <div className="h-[calc(100vh-6rem)] animate-in fade-in zoom-in-95 duration-500">
            <ChatTerminal />
          </div>
        );
      case 'Strategy':
        return (
          <div className="max-w-4xl mx-auto py-20 text-center space-y-10 animate-in fade-in duration-1000 relative">
            {/* Topographic Map Overlay */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <TopographicOverlay />
            </div>

            <div className="relative z-10">
              <div className="inline-flex p-4 bg-primary/10 rounded-full border border-primary/20 mb-4">
                <Globe className="w-12 h-12 text-primary" />
              </div>
              <div className="space-y-4">
                <h2 className="text-3xl font-black text-foreground uppercase tracking-[0.3em] font-[family-name:var(--font-mono)]">Strategic Planning</h2>
                <p className="text-sm text-muted-foreground font-medium max-w-lg mx-auto leading-relaxed normal-case">
                  The AI is compiling global data to build your Q4 market strategy plan.
                </p>
              </div>
              <div className="grid grid-cols-3 gap-6 max-w-2xl mx-auto pt-10">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-[2px] bg-white/[0.04] rounded-full overflow-hidden">
                    <div className="h-full bg-primary/40 w-1/3 animate-loading-bar" />
                  </div>
                ))}
              </div>
              <p className="text-[13px] font-black text-primary/40 uppercase tracking-[0.3em] animate-pulse font-[family-name:var(--font-mono)] mt-6">
                Calculating best strategy path...
              </p>

              {/* Cluster status indicators */}
              <div className="flex justify-center gap-8 mt-12">
                {['APAC Region', 'EMEA Cluster', 'NA Territory'].map((region, i) => (
                  <div key={region} className="text-center space-y-2">
                    <div className="w-3 h-3 rounded-full bg-primary/20 border border-primary/30 mx-auto animate-pulse" style={{ animationDelay: `${i * 0.5}s` }} />
                    <span className="text-[11px] font-bold text-zinc-600 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">{region}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );
      case 'Settings':
        return (
          <div className="max-w-5xl mx-auto space-y-10 animate-in fade-in slide-in-from-right-4 duration-700">
            <h2 className="text-sm font-black text-foreground uppercase tracking-[0.4em] flex items-center gap-4 font-[family-name:var(--font-mono)]">
              <Sliders className="w-4 h-4 text-primary" />
              System Settings
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="glass-card p-8 space-y-6">
                <div className="flex items-center gap-4 text-primary">
                  <Cpu className="w-4 h-4" />
                  <h4 className="text-[13px] font-black uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">Model Configuration</h4>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-white/[0.02] rounded-md border border-white/[0.04]">
                    <span className="text-[13px] font-medium text-muted-foreground">AI Server Endpoint</span>
                    <span className="text-[13px] font-black text-emerald-500 font-[family-name:var(--font-mono)]">ACTIVE: 8000</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white/[0.02] rounded-md border border-white/[0.04] opacity-40">
                    <span className="text-[13px] font-medium text-muted-foreground">Claude-3 Integration</span>
                    <span className="text-[13px] font-black text-zinc-600 font-[family-name:var(--font-mono)]">LOCKED</span>
                  </div>
                </div>
              </div>
              <div className="glass-card p-8 space-y-6">
                <div className="flex items-center gap-4 text-primary">
                  <Lock className="w-4 h-4" />
                  <h4 className="text-[13px] font-black uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">Security Settings</h4>
                </div>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-white/[0.02] rounded-md border border-white/[0.04]">
                    <span className="text-[13px] font-medium text-muted-foreground">Data Encryption</span>
                    <span className="text-[13px] font-black text-primary font-[family-name:var(--font-mono)]">AES-256</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-white/[0.02] rounded-md border border-white/[0.04]">
                    <span className="text-[13px] font-medium text-muted-foreground">Access Level</span>
                    <span className="text-[13px] font-black text-amber-500 font-[family-name:var(--font-mono)]">ADMIN PRIORITY</span>
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

  // ═══ Landing Mode ═══
  if (!consoleActive) {
    return <LandingPage onInitialize={handleInitialize} />;
  }

  // ═══ Console Mode ═══
  return (
    <LoadingContext.Provider value={{ isLoading, setLoading: setIsLoading }}>
      <div className="flex h-screen overflow-hidden bg-background relative">
        {/* Global Loading Bar */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 0.7 }}
              exit={{ scaleX: 1, opacity: 0 }}
              transition={{ duration: 1.5, ease: [0.4, 0, 0.2, 1] }}
              className="fixed top-0 left-0 right-0 h-[2px] bg-primary z-[9999] origin-left pointer-events-none"
            />
          )}
        </AnimatePresence>

        {/* Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed(prev => !prev)}
          systemStatus={systemStatus}
        />

        {/* Main Content */}
        <motion.main
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="flex-1 flex flex-col overflow-hidden relative"
        >
          {/* Header */}
          <header className="h-14 border-b border-white/[0.04] bg-[#050505]/80 backdrop-blur-xl flex items-center justify-between px-6 shrink-0 z-50">
            <div className="flex items-center gap-3 text-[13px] font-bold uppercase tracking-[0.15em] text-zinc-600 font-[family-name:var(--font-mono)]">
              <span
                onClick={() => setActiveTab('Dashboard')}
                className="hover:text-primary cursor-pointer transition-colors duration-150"
              >
                COMMAND
              </span>
              <span className="opacity-20">/</span>
              <span className="text-foreground">{activeTab}</span>
            </div>

            <div className="flex items-center gap-4">
              {/* System status — SVG Waveform */}
              {systemStatus === 'operational' ? (
                <div className="flex items-center gap-1.5">
                  <div className="flex items-center space-x-[2px] h-3">
                    <div className="w-[2px] h-full bg-primary pulse-waveform" style={{ animationDelay: '0ms' }} />
                    <div className="w-[2px] h-full bg-primary pulse-waveform" style={{ animationDelay: '200ms' }} />
                    <div className="w-[2px] h-full bg-primary pulse-waveform" style={{ animationDelay: '400ms' }} />
                  </div>
                  <span className="text-[12px] font-bold text-zinc-600 uppercase tracking-[0.1em] font-[family-name:var(--font-mono)]">
                    ONLINE
                  </span>
                </div>
              ) : (
                <div className="relative flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <div className="absolute inset-0 w-2 h-2 rounded-full bg-red-500/40 animate-ping" />
                  <span className="text-[12px] font-bold text-red-500 uppercase tracking-[0.1em] font-[family-name:var(--font-mono)]">
                    OFFLINE
                  </span>
                </div>
              )}

              <button
                onClick={() => setInsightsOpen(prev => !prev)}
                className={`p-1.5 rounded transition-all duration-150 relative ${
                  insightsOpen ? 'text-primary bg-primary/10 border border-primary/20' : 'text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.03]'
                }`}
                data-tooltip="Proactive Intel"
              >
                <Sparkles className="w-4 h-4" />
                <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-secondary rounded-full animate-pulse" />
              </button>
              <button className="p-1.5 text-zinc-600 hover:text-zinc-400 transition-colors relative">
                <Bell className="w-4 h-4" />
                <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-primary rounded-full" />
              </button>
              <div className="w-7 h-7 rounded-md bg-white/[0.03] border border-white/[0.06] flex items-center justify-center cursor-pointer hover:border-primary/30 transition-all">
                <User className="w-3.5 h-3.5 text-zinc-500" />
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 relative scroll-smooth scrollbar-tactical">
            <div className="max-w-[1500px] mx-auto">
              {renderContent()}
            </div>
          </div>
        </motion.main>
        
        {/* Proactive Intel Sidebar Drawer */}
        <ProactiveInsights isOpen={insightsOpen} onClose={() => setInsightsOpen(false)} />

        {/* Tactical Scanline Overlay — placed at end with pointer-events-none to prevent click interference */}
        <div className="absolute inset-0 scanlines z-[9999] pointer-events-none" />
      </div>
    </LoadingContext.Provider>
  );
}
