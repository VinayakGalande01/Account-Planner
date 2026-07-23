'use client';

// LEGACY/BACKUP FILE — not part of the active build (frontend/src is the live app).
// Original single-account drill-down view: header with tier badge + action buttons,
// a health-index radial gauge with risk callouts, a revenue trend sparkline, and
// tables for open opportunities and key contacts (fetched from /api/accounts/:id/details).
//
// --- SECTION: Shared UI Helpers (TacticalTooltip, formatCurrency, MicroTrend chart) ---
// --- SECTION: AccountDetail Component — data fetch + derived values ---
// --- SECTION: Render — Header (name, tier, action buttons) ---
// --- SECTION: Render — Health Index & Active Risks ---
// --- SECTION: Render — Revenue Forecast, Opportunity Table, Contact Matrix ---

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Users, DollarSign,
  TrendingUp, Building2,
  Download, Globe, Database, BarChart3, Sparkles,
  Info, AlertCircle
} from 'lucide-react';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';


interface AccountDetailProps {
  account: any;
  onBack: () => void;
}

// Reusable Tactical Tooltip Component
function TacticalTooltip({ content }: { content: string }) {
  const [visible, setVisible] = useState(false);
  
  return (
    <div className="relative inline-flex items-center ml-2 group" 
         onMouseEnter={() => setVisible(true)} 
         onMouseLeave={() => setVisible(false)}>
      <Info className="w-3 h-3 text-zinc-600 hover:text-primary transition-colors cursor-help" />
      <AnimatePresence>
        {visible && (
          <motion.div 
            initial={{ opacity: 0, y: 5, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 5, scale: 0.95 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-zinc-900 border border-primary/20 rounded shadow-2xl z-[100] pointer-events-none"
          >
            <div className="text-[13px] font-medium text-zinc-300 leading-normal font-[family-name:var(--font-inter)]">
              {content}
            </div>
            <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-zinc-900 border-r border-b border-primary/20 rotate-45 -mt-1" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
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
  const { setActiveTab, setAiCommand } = useData();
  const { authFetch } = useAuth();
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    authFetch(`/api/accounts/${account.Account_ID}/details`)
      .then(res => res.json())
      .then(data => {
        setDetails(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [account.Account_ID]);


  const handleLaunchIntel = () => {
    setAiCommand(`Give me a detailed strategic health check on ${account.Account_Name}. Focus on current pipeline and engagement risks.`);
    setActiveTab('Intelligence');
  };

  const healthScore = account.health_score ?? 84;
  const healthColor = healthScore >= 80 ? '#10b981' : healthScore >= 60 ? '#f59e0b' : healthScore >= 40 ? '#f97316' : '#ef4444';

  const opportunities = details?.opportunities || [];
  const contacts = details?.contacts || [];
  const cases = details?.cases || [];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 pb-10"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-5">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-muted rounded-md border border-border transition-all text-zinc-600 hover:text-primary"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="h-6 w-px bg-border hidden sm:block" />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-black text-foreground tracking-tight uppercase font-[family-name:var(--font-mono)]">
                {account.Account_Name}
              </h1>
              <span className={`px-2 py-0.5 rounded text-[11px] font-black uppercase border ${getTierStyle(account.Account_Tier)}`}>
                {account.Account_Tier}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-[12px] font-medium text-zinc-600 uppercase tracking-[0.1em] flex items-center gap-1.5 font-[family-name:var(--font-mono)]">
                <Globe className="w-3 h-3" /> {account.Territory || 'GLOBAL'}
              </span>
              <span className="text-[12px] font-medium text-zinc-600 uppercase tracking-[0.1em] flex items-center gap-1.5 font-[family-name:var(--font-mono)]">
                <Database className="w-3 h-3" /> {account.Account_ID}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handleLaunchIntel}
            className="px-3 py-1.5 bg-primary/10 text-primary text-[13px] font-bold rounded-md uppercase border border-primary/20 hover:bg-primary/20 transition-all flex items-center gap-2 font-[family-name:var(--font-mono)]"
          >
            <Sparkles className="w-3 h-3" /> Launch Intel
          </button>
          <button className="px-3 py-1.5 bg-muted text-zinc-500 text-[13px] font-bold rounded-md uppercase border border-border hover:bg-muted/80 transition-all flex items-center gap-2 font-[family-name:var(--font-mono)]">
            <Download className="w-3 h-3" /> Export
          </button>
          <button className="px-3 py-1.5 bg-primary text-white text-[13px] font-bold rounded-md uppercase shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all flex items-center gap-2 font-[family-name:var(--font-mono)]">
            <TrendingUp className="w-3 h-3" /> Report
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Health Index */}
        <div className="bg-card border border-border p-5 rounded-md space-y-5 relative overflow-hidden">
          <div className="flex items-center">
            <p className="text-[12px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Relational Health Index
            </p>
            <TacticalTooltip content="A 0-100 score synthesized from revenue, relationship depth, engagement, and support history." />
          </div>
          <div className="flex items-center justify-between">
            <div className="relative w-20 h-20 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="34" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-muted" />
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
                <span className="text-[12px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Sentiment: Positive</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-sm bg-amber-500" />
                <span className="text-[12px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Engagement: High</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-sm bg-primary" />
                <span className="text-[12px] font-medium text-zinc-400 font-[family-name:var(--font-mono)]">Next Event: QBR (12d)</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border">
            <div className="flex items-center mb-3">
              <p className="text-[12px] font-black text-red-500 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">Active Risks</p>
              <TacticalTooltip content="Critical flags detected by the APEX engine, such as stalled deals or support issues." />
            </div>
            <div className="space-y-2">
              {cases.filter((c:any) => c.severity === 'Critical' || c.severity === 'High').length > 0 ? (
                cases.filter((c:any) => c.severity === 'Critical' || c.severity === 'High').map((c:any, i:number) => (
                  <div key={i} className="p-3 bg-red-500/[0.04] border border-red-500/10 rounded-md">
                    <p className="text-[13px] font-bold text-foreground">{c.subject}</p>
                    <p className="text-[12px] text-zinc-500 mt-1 leading-relaxed">Status: {c.status} | Severity: {c.severity}</p>
                  </div>
                ))
              ) : (
                <div className="p-3 bg-muted/30 border border-border rounded-md border-dashed">
                  <p className="text-[12px] text-zinc-600 dark:text-zinc-500 italic">No critical risks detected in current cycle.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Revenue & Trend */}
        <div className="lg:col-span-2 bg-card border border-border p-5 rounded-md space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <p className="text-[12px] font-black text-zinc-600 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                Revenue Forecast & Velocity
              </p>
              <TacticalTooltip content="Projected earnings and the rate of deal movement compared to previous periods." />
            </div>
            <div className="flex gap-4">
              <div className="text-right">
                <p className="text-sm font-black text-foreground data-cell">{formatCurrency(account.total_pipeline_value)}</p>
                <p className="text-[11px] text-zinc-600 font-black uppercase font-[family-name:var(--font-mono)]">ACV Portfolio</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-black text-emerald-500 data-cell">+14%</p>
                <p className="text-[11px] text-zinc-600 dark:text-zinc-500 font-black uppercase font-[family-name:var(--font-mono)]">Growth Rate</p>
              </div>
            </div>
          </div>
          <div className="bg-muted/30 rounded p-3 border border-border">
            <MicroTrend />
          </div>
        </div>

        {/* Bottom Widgets */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* Opportunity Table */}
          <div className="md:col-span-2 bg-card border border-border rounded-md overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center shrink-0">
              <h4 className="text-[12px] font-black uppercase text-foreground tracking-[0.15em] font-[family-name:var(--font-mono)]">
                Active Opportunity Pipeline
              </h4>
              <TacticalTooltip content="Real-time tracking of all open deals, grouped by their tactical progression stage." />
            </div>
            <div className="flex-1 overflow-y-auto max-h-[250px] scrollbar-hide">
              <table className="w-full text-left text-[13px]">
                <thead className="sticky top-0 bg-card z-20">
                  <tr className="border-b border-border bg-muted/30">
                    <th className="px-4 py-2 font-bold text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.06em] font-[family-name:var(--font-mono)]">Deal Name</th>
                    <th className="px-4 py-2 font-bold text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.06em] text-center font-[family-name:var(--font-mono)]">Stage</th>
                    <th className="px-4 py-2 font-bold text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.06em] text-right font-[family-name:var(--font-mono)]">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <tr key={i} className="border-b border-border/40 animate-pulse">
                        <td className="px-4 py-3"><div className="h-2 bg-muted rounded w-3/4" /></td>
                        <td className="px-4 py-3"><div className="h-2 bg-muted rounded w-1/2 mx-auto" /></td>
                        <td className="px-4 py-3"><div className="h-2 bg-muted rounded w-1/2 ml-auto" /></td>
                      </tr>
                    ))
                  ) : opportunities.length > 0 ? (
                    opportunities.map((deal: any, i: number) => (
                    <tr key={i} className="border-b border-border/40 hover:bg-muted/50 transition-colors" style={{ height: '40px' }}>
                      <td className="px-4 py-0 font-bold text-foreground truncate max-w-[200px]">{deal.name}</td>
                      <td className="px-4 py-0 text-center">
                        <span className="px-1.5 py-0.5 bg-muted border border-border rounded text-[11px] uppercase font-bold text-zinc-500 font-[family-name:var(--font-mono)]">
                          {deal.stage}
                        </span>
                      </td>
                      <td className="px-4 py-0 text-right font-black text-primary data-cell">{formatCurrency(deal.value)}</td>
                    </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-4 py-8 text-center text-zinc-600 dark:text-zinc-500 italic">No open opportunities found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Contact Matrix */}
          <div className="bg-card border border-border rounded-md overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between shrink-0">
              <div className="flex items-center">
                <h4 className="text-[12px] font-black uppercase text-foreground tracking-[0.15em] font-[family-name:var(--font-mono)]">Key Contacts</h4>
                <TacticalTooltip content="Verified stakeholders and decision-makers within the organization." />
              </div>
              <Users className="w-3 h-3 text-zinc-600" />
            </div>
            <div className="p-3 space-y-3 flex-1 overflow-y-auto max-h-[250px] scrollbar-hide">
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3 animate-pulse">
                    <div className="w-7 h-7 rounded bg-muted" />
                    <div className="flex-1 space-y-2">
                      <div className="h-2 bg-muted rounded w-1/2" />
                      <div className="h-2 bg-muted rounded w-1/3" />
                    </div>
                  </div>
                ))
              ) : contacts.length > 0 ? (
                contacts.map((contact: any, i: number) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded bg-muted border border-border flex items-center justify-center font-black text-[12px] text-zinc-500 font-[family-name:var(--font-mono)]">
                    {contact.first_name[0]}{contact.last_name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-bold truncate text-foreground">{contact.first_name} {contact.last_name}</p>
                    <p className="text-[11px] text-zinc-600 dark:text-zinc-500 truncate font-medium">{contact.role}</p>
                  </div>
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${contact.engagement === 'High' ? 'bg-emerald-500' : contact.engagement === 'Medium' ? 'bg-amber-500' : 'bg-zinc-600'}`} title={contact.engagement} />
                </div>
                ))
              ) : (
                <p className="text-[12px] text-zinc-600 dark:text-zinc-500 italic text-center py-4">No contacts on record</p>
              )}
              <button className="w-full py-2 bg-muted hover:bg-muted/80 text-[12px] font-bold uppercase rounded-md border border-border transition-all text-zinc-600 font-[family-name:var(--font-mono)] tracking-[0.1em]">
                View Directory
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
