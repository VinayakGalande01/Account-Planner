'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  AlertTriangle,
  Building2,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { Brackets } from './Brackets';

interface AccountMock {
  name: string;
  tier: string;
  health: number;
  acv: string;
  trend: 'up' | 'down';
}

const ACCOUNTS: AccountMock[] = [
  { name: 'Helix Capital', tier: 'T-1', health: 92, acv: '$1.2M', trend: 'up' },
  { name: 'Northwind', tier: 'T-1', health: 78, acv: '$880K', trend: 'up' },
  { name: 'Vector Robotics', tier: 'T-2', health: 54, acv: '$340K', trend: 'down' },
  { name: 'Solace Health', tier: 'T-2', health: 41, acv: '$210K', trend: 'down' },
  { name: 'Orbital Logistics', tier: 'T-3', health: 86, acv: '$190K', trend: 'up' },
];

const healthColor = (h: number): string =>
  h >= 75 ? 'bg-primary' : h >= 50 ? 'bg-[color:var(--color-warning)]' : 'bg-red-500';

interface DashboardPreviewProps {
  compact?: boolean;
}

export const DashboardPreview: React.FC<DashboardPreviewProps> = ({ compact = false }) => {
  return (
    <div
      data-testid="dashboard-preview"
      className="relative glass brackets scanlines overflow-hidden rounded-md border border-primary/20"
    >
      {/* sweep line */}
      <div className="absolute inset-x-0 h-px bg-primary/40 pointer-events-none scan-sweep z-10" />

      {/* Header bar */}
      <div className="relative flex items-center justify-between px-4 py-3 border-b border-primary/15 z-10 bg-black/10">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span className="w-2 h-2 rounded-full bg-[color:var(--color-warning)]" />
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="ml-3 font-mono text-[10px] tracking-[0.25em] uppercase text-muted-foreground">
            apex://workspace/q4-2026
          </span>
        </div>
        <div className="font-mono text-[10px] tracking-widest text-primary terminal-cursor">
          LIVE
        </div>
      </div>

      <div className={`relative p-4 ${compact ? '' : 'lg:p-6'} grid grid-cols-12 gap-3 z-[2]`}>
        {/* Pipeline summary */}
        <div className="col-span-12 sm:col-span-7 border border-primary/15 bg-background/40 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="label-tag">Pipeline Velocity</div>
            <TrendingUp className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="font-display text-4xl font-bold tracking-tight text-left">
            $4.82<span className="text-primary font-sans font-medium">M</span>
          </div>
          <div className="text-[11px] font-mono text-muted-foreground text-left mt-1">
            Weighted ACV · +12.4% wow
          </div>

          {/* mini bar chart */}
          <div className="flex items-end gap-1.5 h-16 mt-4">
            {[40, 55, 48, 62, 70, 58, 78, 84, 72, 88, 95, 90].map((h, i) => (
              <div
                key={i}
                className="flex-1 bg-primary/80 hover:bg-primary transition-all"
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
          <div className="flex justify-between mt-1.5 font-mono text-[9px] tracking-widest text-muted-foreground">
            <span>JAN</span>
            <span>JUN</span>
            <span>DEC</span>
          </div>
        </div>

        {/* Health gauge */}
        <div className="col-span-12 sm:col-span-5 border border-primary/15 bg-background/40 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="label-tag">Relational Health</div>
            <Sparkles className="w-3.5 h-3.5 text-primary" />
          </div>
          {/* radial */}
          <div className="flex-1 grid place-items-center py-2">
            <div className="relative w-24 h-24">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke="currentColor"
                  className="text-primary/15"
                  strokeWidth="6"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke="currentColor"
                  className="text-primary"
                  strokeWidth="6"
                  strokeDasharray={`${(82 / 100) * 264} 264`}
                  strokeLinecap="round"
                  style={{ filter: 'drop-shadow(0 0 6px hsl(var(--primary) / 0.6))' }}
                />
              </svg>
              <div className="absolute inset-0 grid place-items-center">
                <div className="text-center">
                  <div className="font-display text-2xl font-bold">82</div>
                  <div className="text-[8px] font-mono tracking-widest text-muted-foreground">
                    STRONG
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Account directory */}
        <div className="col-span-12 border border-primary/15 bg-background/40">
          <div className="px-4 py-2.5 border-b border-primary/15 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-primary" />
              <span className="label-tag">Account Directory</span>
            </div>
            <span className="font-mono text-[10px] text-muted-foreground">
              {ACCOUNTS.length} active
            </span>
          </div>
          <ul className="divide-y divide-primary/10">
            {ACCOUNTS.slice(0, compact ? 4 : 5).map((a) => (
              <li
                key={a.name}
                className="px-4 py-2.5 flex items-center gap-3 hover:bg-primary/5 transition-colors text-left"
              >
                <span className="font-mono text-[10px] tracking-widest text-primary border border-primary/40 px-1.5 py-0.5">
                  {a.tier}
                </span>
                <span className="flex-1 text-sm font-medium truncate">{a.name}</span>
                <span className="hidden sm:inline font-mono text-[11px] text-muted-foreground tabular-nums w-16 text-right">
                  {a.acv}
                </span>
                <div className="w-20 h-1.5 bg-primary/10 relative overflow-hidden hidden xs:block">
                  <div
                    className={`h-full ${healthColor(a.health)}`}
                    style={{ width: `${a.health}%` }}
                  />
                </div>
                <span className="font-mono text-[11px] tabular-nums w-8 text-right">
                  {a.health}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* AI Terminal + insight */}
        <div className="col-span-12 sm:col-span-7 border border-primary/15 bg-black/40 dark:bg-black/60 p-3 font-mono text-[11px] text-left">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-primary">▮</span>
            <span className="text-[10px] tracking-[0.25em] uppercase text-primary font-bold">
              AI Assistant
            </span>
          </div>
          <div className="space-y-1.5 leading-relaxed">
            <div className="text-muted-foreground">
              <span className="text-primary">apex&gt;</span> risk on Vector Robotics?
            </div>
            <div className="text-foreground/90">
              Warning: Only 1 contact has replied in the last month, and there are{' '}
              <span className="text-red-500 font-bold">2 urgent</span> support tickets.
            </div>
            <div className="text-foreground/70">
              Recommendation: Schedule a call with their leadership team.
            </div>
            <div className="text-muted-foreground terminal-cursor">
              <span className="text-primary">apex&gt;</span>{' '}
            </div>
          </div>
        </div>

        {/* Insight alert */}
        <div className="col-span-12 sm:col-span-5 border border-red-500/40 bg-red-500/5 p-3 text-left">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
            <span className="font-mono text-[10px] tracking-[0.25em] uppercase text-red-500 font-bold">
              Warning Alert
            </span>
          </div>
          <div className="text-sm leading-snug font-bold">
            Solace Health's score dropped.
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">
            They have 3 open support tickets. High risk of leaving soon.
          </div>
          <button
            data-testid="preview-insight-action"
            className="mt-3 inline-flex items-center gap-1 text-[10px] font-mono tracking-widest text-primary hover:text-primary uppercase cursor-pointer bg-transparent border-none p-0"
          >
            Solve Issues <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};
