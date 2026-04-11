'use client';

import React from 'react';
import { 
  Briefcase, Users, PieChart, Sparkles, 
  Target, Settings, LayoutDashboard, Database, 
  TrendingUp, ShieldCheck 
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const menuItems = [
    { id: 'Portfolio', icon: LayoutDashboard },
    { id: 'Accounts', icon: Users },
    { id: 'Pipeline', icon: TrendingUp },
    { id: 'Intelligence', icon: Sparkles },
    { id: 'Strategy', icon: Target },
    { id: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-white/5 bg-card flex flex-col h-full shrink-0">
      <div className="p-6 border-b border-white/5 flex items-center gap-3">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center font-black text-background text-sm shadow-[0_0_15px_rgba(234,179,8,0.4)]">
          AP
        </div>
        <span className="font-black text-sm tracking-widest text-primary uppercase">Planner Agent</span>
      </div>
      
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button 
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-[10px] font-black uppercase tracking-[0.15em] transition-all group ${
                isActive 
                  ? 'bg-primary/10 text-primary border border-primary/20 shadow-[inset_0_0_10px_rgba(234,179,8,0.05)]' 
                  : 'text-muted-foreground hover:bg-white/5 hover:text-foreground border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground/50 group-hover:text-foreground'}`} />
              {item.id}
            </button>
          );
        })}
      </nav>

      <div className="p-6 border-t border-white/5">
        <div className="p-4 bg-primary/5 rounded-xl border border-primary/10 relative overflow-hidden group hover:border-primary/30 transition-all">
          <div className="absolute -right-4 -bottom-4 w-12 h-12 bg-primary/10 rounded-full blur-xl group-hover:bg-primary/20 transition-all" />
          <p className="text-[9px] font-black text-primary uppercase tracking-[0.2em] mb-2 flex items-center gap-2">
            <ShieldCheck className="w-3 h-3" />
            AI Status
          </p>
          <p className="text-[10px] text-muted-foreground leading-relaxed font-bold">
            All systems nominal. Analyzing global portfolio...
          </p>
        </div>
      </div>
    </aside>
  );
}
