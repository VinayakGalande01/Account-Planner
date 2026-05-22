'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, Users, TrendingUp, Sparkles,
  Target, Settings, ChevronLeft, ChevronRight,
  ShieldCheck, Activity,
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  systemStatus: 'operational' | 'offline' | 'connecting';
}

const menuItems = [
  { id: 'Dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'Accounts', label: 'Accounts', icon: Users },
  { id: 'Pipeline', label: 'Pipeline', icon: TrendingUp },
  { id: 'Intelligence', label: 'AI Assistant', icon: Sparkles },
  { id: 'Strategy', label: 'Strategy', icon: Target },
  { id: 'Settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ activeTab, onTabChange, isCollapsed, onToggleCollapse, systemStatus }: SidebarProps) {
  const statusColor = systemStatus === 'operational' ? 'text-emerald-500' : systemStatus === 'connecting' ? 'text-amber-500' : 'text-red-500';
  const statusLabel = systemStatus === 'operational' ? 'SYSTEM ONLINE' : systemStatus === 'connecting' ? 'CONNECTING...' : 'OFFLINE';

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 64 : 240 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className="border-r border-white/[0.04] bg-[#050505] flex flex-col h-full shrink-0 overflow-hidden relative z-40"
    >
      {/* Logo */}
      <div className="h-16 border-b border-white/[0.04] flex items-center gap-3 px-4 shrink-0">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center font-black text-white text-[12px] shrink-0 shadow-[0_0_20px_rgba(37,99,235,0.3)]">
          AP
        </div>
        {!isCollapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="font-black text-[12px] tracking-[0.15em] text-primary uppercase whitespace-nowrap font-[family-name:var(--font-mono)]"
          >
            APEX PLANNER
          </motion.span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto scrollbar-hide">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              data-tooltip={isCollapsed ? item.label : undefined}
              className={`w-full flex items-center gap-3 rounded-md transition-all duration-150 group relative ${
                isCollapsed ? 'px-0 py-2.5 justify-center' : 'px-3 py-2.5'
              } ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-zinc-500 hover:bg-white/[0.03] hover:text-zinc-300'
              }`}
            >
              <Icon className={`w-[18px] h-[18px] shrink-0 transition-colors duration-150 ${
                isActive ? 'text-primary' : 'text-zinc-600 group-hover:text-zinc-400'
              }`} />
              {!isCollapsed && (
                <span className="text-[13px] font-bold uppercase tracking-[0.12em] whitespace-nowrap">
                  {item.label}
                </span>
              )}
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-primary rounded-r-full"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* System Status */}
      <div className="px-2 pb-2 shrink-0">
        {!isCollapsed ? (
          <div className="p-3 bg-white/[0.02] rounded-md border border-white/[0.04] space-y-2">
            <div className="flex items-center gap-2">
              <Activity className={`w-3 h-3 ${statusColor}`} />
              <span className={`text-[12px] font-bold uppercase tracking-[0.15em] ${statusColor} font-[family-name:var(--font-mono)]`}>
                {statusLabel}
              </span>
            </div>
            <p className="text-[12px] text-zinc-600 leading-relaxed font-medium">
              Backend: :8002 · LLM: :8000
            </p>
          </div>
        ) : (
          <div className="flex justify-center py-2" data-tooltip="System Status">
            <div className={`w-2 h-2 rounded-full ${
              systemStatus === 'operational' ? 'bg-emerald-500' : systemStatus === 'connecting' ? 'bg-amber-500' : 'bg-red-500'
            } animate-pulse`} />
          </div>
        )}
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggleCollapse}
        className="h-10 border-t border-white/[0.04] flex items-center justify-center text-zinc-600 hover:text-zinc-400 hover:bg-white/[0.03] transition-all shrink-0"
      >
        {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>
    </motion.aside>
  );
}
