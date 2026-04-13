'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft, Users, DollarSign,
  TrendingUp, Building2,
  Download, Globe, Database, BarChart3
} from 'lucide-react';

interface AccountDetailProps {
  account: any;
  onBack: () => void;
}

function formatCurrency(val: number | undefined): string {
  if (!val && val !== 0) return '—';
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

function getTierStyle(tier: string): string {
  switch (tier) {
    case 'Strategic': return 'bg-amber-500/10 border-amber-500/20 text-amber-500';
    case 'Key': return 'bg-blue-500/10 border-blue-500/20 text-blue-500';
    default: return 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400';
  }
}

// Inline SVG micro-chart for revenue trend
function MicroTrend() {
  const data = [28, 35, 30, 45, 42, 55, 60, 58, 72, 68, 75, 80];
  const max = Math.max(...data);
  const w = 120;
  const h = 40;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - (v / max) * h;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-16">
      <defs>
        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#2563eb" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${h} ${points} ${w},${h}`}
        fill="url(#trendGrad)"
      />
      <polyline
        points={points}
        fill="none"
        stroke="#2563eb"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function AccountDetail({ account, onBack }: AccountDetailProps) {
  const healthScore = account.health_score ?? 84;
  const healthColor = healthScore >= 80 ? '#10b981' : healthScore >= 60 ? '#f59e0b' : healthScore >= 40 ? '#f97316' : '#ef4444';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 pb-10"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.04] pb-5">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-white/[0.04] rounded-md border border-white/[0.04] transition-all text-zinc-600 hover:text-primary"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="h-6 w-px bg-white/[0.06] hidden sm:block" />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-black text-foreground tracking-tight uppercase font-[family-name:var(--font-mono)]">
                {account.Account_Name}
              </h1>
              <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase border ${getTierStyle(account.Account_Tier)}`}>
                {account.Account_Tier}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-[9px] font-medium text-zinc-600 uppercase tracking-[0.1em] flex items-center gap-1.5 font-[family-name:var(--font-mono)]">
                <Globe className="w-3 h-3" /> {account.Territory || 'GLOBAL'}
              </span>
              <span className="text-[9px] font-medium text-zinc-600 uppercase tracking-[0.1em] flex items-center gap-1.5 font-[family-name:var(--font-mono)]">
                <Database className="w-3 h-3" /> {account.Account_ID}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1.5 bg-white/[0.03] text-zinc-500 text-[10px] font-bold rounded-md uppercase border border-white/[0.04] hover:bg-white/[0.06] transition-all flex items-center gap-2 font-[family-name:var(--font-mono)]">
            <Download className="w-3 h-3" /> Export
          </button>
          <button className="px-3 py-1.5 bg-primary text-white text-[10px] font-bold rounded-md uppercase shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all flex items-center gap-2 font-[family-name:var(--font-mono)]">
            <TrendingUp className="w-3 h-3" /> Report
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Health Index */}
        <div className="bg-[#080808] border border-white/[0.04] p-5 rounded-md space-y-5">
          <p className="text-[9px] font-black text-zinc-600 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
            Relational Health Index
          </p>
          <div className="flex items-center justify-between">
            <div className="relative w-20 h-20 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="34" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-white/[0.04]" />
                <circle
                  cx="40" cy="40" r="34"
                  stroke={healthColor}
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray={Math.PI * 68}
                  strokeDashoffset={Math.PI * 68 * (1 - healthScore / 100)}
                  strokeLinecap="round"
                  className="transition-all duration-1000"
                />
              </svg>
              <span className="absolute text-xl font-black text-foreground data-cell">{healthScore}</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-sm bg-emerald-500" />
                <span className="text-[9px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Sentiment: Positive</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-sm bg-amber-500" />
                <span className="text-[9px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Engagement: High</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-sm bg-primary" />
                <span className="text-[9px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Next Event: QBR (12d)</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.04]">
            <p className="text-[9px] font-black text-red-500 uppercase tracking-[0.15em] mb-3 font-[family-name:var(--font-mono)]">Active Risks</p>
            <div className="space-y-2">
              <div className="p-3 bg-red-500/[0.04] border border-red-500/10 rounded-md">
                <p className="text-[10px] font-bold text-foreground">Competitor Contract Expiry (Dec 2026)</p>
                <p className="text-[9px] text-zinc-500 mt-1 leading-relaxed">Immediate outreach required to lock renewal terms.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Revenue & Trend */}
        <div className="lg:col-span-2 bg-[#080808] border border-white/[0.04] p-5 rounded-md space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-[9px] font-black text-zinc-600 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Revenue Forecast & Velocity
            </p>
            <div className="flex gap-4">
              <div className="text-right">
                <p className="text-sm font-black text-foreground data-cell">{formatCurrency(account.total_pipeline_value || 4500000)}</p>
                <p className="text-[8px] text-zinc-600 font-black uppercase font-[family-name:var(--font-mono)]">ACV Portfolio</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-black text-emerald-500 data-cell">+14%</p>
                <p className="text-[8px] text-zinc-600 font-black uppercase font-[family-name:var(--font-mono)]">Growth Rate</p>
              </div>
            </div>
          </div>
          <div className="bg-white/[0.01] rounded p-3 border border-white/[0.03]">
            <MicroTrend />
          </div>
        </div>

        {/* Bottom Widgets */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* Opportunity Table */}
          <div className="md:col-span-2 bg-[#080808] border border-white/[0.04] rounded-md overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.04] bg-white/[0.01]">
              <h4 className="text-[9px] font-black uppercase text-foreground tracking-[0.15em] font-[family-name:var(--font-mono)]">
                Active Opportunity Pipeline
              </h4>
            </div>
            <table className="w-full text-left text-[10px]">
              <thead>
                <tr className="border-b border-white/[0.04] bg-white/[0.01]">
                  <th className="px-4 py-2 font-bold text-zinc-600 uppercase tracking-[0.06em] font-[family-name:var(--font-mono)]">Deal Name</th>
                  <th className="px-4 py-2 font-bold text-zinc-600 uppercase tracking-[0.06em] text-center font-[family-name:var(--font-mono)]">Stage</th>
                  <th className="px-4 py-2 font-bold text-zinc-600 uppercase tracking-[0.06em] text-right font-[family-name:var(--font-mono)]">Value</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { name: 'Global Cloud Migration', stage: 'Contracting', value: '$2.5M' },
                  { name: 'Cybersecurity Suite Upgrade', stage: 'Negotiation', value: '$1.2M' },
                  { name: 'Data Lake Pilot', stage: 'Discovery', value: '$450K' },
                ].map((deal, i) => (
                  <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.01] transition-colors" style={{ height: '36px' }}>
                    <td className="px-4 py-0 font-bold text-foreground">{deal.name}</td>
                    <td className="px-4 py-0 text-center">
                      <span className="px-1.5 py-0.5 bg-white/[0.03] border border-white/[0.06] rounded text-[8px] uppercase font-bold text-zinc-500 font-[family-name:var(--font-mono)]">
                        {deal.stage}
                      </span>
                    </td>
                    <td className="px-4 py-0 text-right font-black text-primary data-cell">{deal.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Contact Matrix */}
          <div className="bg-[#080808] border border-white/[0.04] rounded-md overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.04] bg-white/[0.01] flex items-center justify-between">
              <h4 className="text-[9px] font-black uppercase text-foreground tracking-[0.15em] font-[family-name:var(--font-mono)]">Key Contacts</h4>
              <Users className="w-3 h-3 text-zinc-600" />
            </div>
            <div className="p-3 space-y-3">
              {[
                { initials: 'JS', name: 'John Smith', role: 'Chief Technology Officer' },
                { initials: 'AP', name: 'Alice Park', role: 'VP Engineering' },
              ].map((contact, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded bg-white/[0.03] border border-white/[0.06] flex items-center justify-center font-black text-[9px] text-zinc-500 font-[family-name:var(--font-mono)]">
                    {contact.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold truncate text-foreground">{contact.name}</p>
                    <p className="text-[8px] text-zinc-600 truncate font-medium">{contact.role}</p>
                  </div>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" title="Highly Engaged" />
                </div>
              ))}
              <button className="w-full py-2 bg-white/[0.02] hover:bg-white/[0.04] text-[9px] font-bold uppercase rounded-md border border-white/[0.04] transition-all text-zinc-600 font-[family-name:var(--font-mono)] tracking-[0.1em]">
                View Directory
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
