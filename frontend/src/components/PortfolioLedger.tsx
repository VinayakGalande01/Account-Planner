'use client';

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ChevronDown, ChevronUp, MoreHorizontal, Flag, Terminal, Edit, ChevronsUpDown } from 'lucide-react';

interface PortfolioLedgerProps {
  accounts: any[];
  loading: boolean;
  search: string;
  onSearchChange: (val: string) => void;
  onAccountClick: (acc: any) => void;
}

type SortKey = 'Account_Name' | 'Account_Tier' | 'health_score' | 'total_pipeline_value';
type SortDir = 'asc' | 'desc';

function formatCurrency(val: number | undefined): string {
  if (!val && val !== 0) return '—';
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

function getRelativeTime(dateStr: string | undefined): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return '1d ago';
  if (diffDays < 30) return `${diffDays}d ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}y ago`;
}

function getTierStyle(tier: string): string {
  switch (tier) {
    case 'Strategic': return 'bg-amber-500/10 border-amber-500/20 text-amber-500';
    case 'Key': return 'bg-blue-500/10 border-blue-500/20 text-blue-500';
    case 'Growth': return 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400';
    default: return 'bg-zinc-500/10 border-zinc-500/20 text-zinc-500';
  }
}

function getHealthColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}

export default function PortfolioLedger({ accounts, loading, search, onSearchChange, onAccountClick }: PortfolioLedgerProps) {
  const [sortKey, setSortKey] = useState<SortKey>('Account_Name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [tierFilter, setTierFilter] = useState<string>('all');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <ChevronsUpDown className="w-2.5 h-2.5 opacity-20" />;
    return sortDir === 'asc' ? <ChevronUp className="w-2.5 h-2.5 text-primary" /> : <ChevronDown className="w-2.5 h-2.5 text-primary" />;
  };

  const processedAccounts = useMemo(() => {
    let result = accounts.filter(acc =>
      acc.Account_Name?.toLowerCase().includes(search.toLowerCase())
    );
    if (tierFilter !== 'all') {
      result = result.filter(acc => acc.Account_Tier === tierFilter);
    }
    result.sort((a, b) => {
      const valA = a[sortKey] ?? '';
      const valB = b[sortKey] ?? '';
      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDir === 'asc' ? valA - valB : valB - valA;
      }
      return sortDir === 'asc'
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });
    return result;
  }, [accounts, search, tierFilter, sortKey, sortDir]);

  const tiers = useMemo(() => {
    const set = new Set(accounts.map(a => a.Account_Tier).filter(Boolean));
    return Array.from(set);
  }, [accounts]);

  return (
    <div className="corner-brackets bg-[#080808] rounded-md overflow-hidden">
      {/* Header Bar */}
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between bg-white/[0.01]">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-black uppercase tracking-[0.4em] text-foreground font-[family-name:var(--font-mono)]">
            Portfolio Ledger
          </h3>
          <span className="text-[9px] font-bold text-zinc-600 font-[family-name:var(--font-mono)]">
            {processedAccounts.length} records
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-600" />
            <input
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Filter..."
              className="bg-white/[0.02] border border-white/[0.04] rounded-md pl-7 pr-3 py-1.5 text-[10px] focus:outline-none focus:border-primary/30 text-foreground placeholder:text-zinc-700 w-36 font-[family-name:var(--font-mono)]"
            />
          </div>
          {/* Tier Filter */}
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-white/[0.02] border border-white/[0.04] rounded-md px-2 py-1.5 text-[10px] text-zinc-400 focus:outline-none focus:border-primary/30 font-[family-name:var(--font-mono)] uppercase appearance-none cursor-pointer"
          >
            <option value="all">All Tiers</option>
            {tiers.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto scrollbar-tactical" style={{ perspective: '1000px' }}>
        <table className="w-full text-left text-[11px] border-collapse">
          <thead>
            <tr className="border-b border-white/[0.04] bg-white/[0.01]">
              <th
                className="px-4 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] cursor-pointer hover:text-zinc-400 transition-colors select-none font-[family-name:var(--font-mono)]"
                onClick={() => handleSort('Account_Name')}
              >
                <span className="inline-flex items-center gap-1.5">Account <SortIcon column="Account_Name" /></span>
              </th>
              <th className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-center font-[family-name:var(--font-mono)]">Industry</th>
              <th className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-center font-[family-name:var(--font-mono)]">Territory</th>
              <th
                className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-center cursor-pointer hover:text-zinc-400 transition-colors select-none font-[family-name:var(--font-mono)]"
                onClick={() => handleSort('Account_Tier')}
              >
                <span className="inline-flex items-center gap-1.5">Tier <SortIcon column="Account_Tier" /></span>
              </th>
              <th
                className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-center cursor-pointer hover:text-zinc-400 transition-colors select-none font-[family-name:var(--font-mono)]"
                onClick={() => handleSort('health_score')}
              >
                <span className="inline-flex items-center gap-1.5">Health <SortIcon column="health_score" /></span>
              </th>
              <th
                className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-right cursor-pointer hover:text-zinc-400 transition-colors select-none font-[family-name:var(--font-mono)]"
                onClick={() => handleSort('total_pipeline_value')}
              >
                <span className="inline-flex items-center gap-1.5 justify-end">Pipeline <SortIcon column="total_pipeline_value" /></span>
              </th>
              <th className="px-3 py-2.5 font-bold uppercase text-zinc-600 tracking-[0.08em] text-center font-[family-name:var(--font-mono)]">Last Activity</th>
              <th className="px-3 py-2.5 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <>
                {/* Ghost skeleton rows */}
                {Array.from({ length: 6 }).map((_, rowIdx) => (
                  <tr key={rowIdx} className="border-b border-white/[0.02] ghost-row" style={{ height: '36px', animationDelay: `${rowIdx * 0.2}s` }}>
                    <td className="px-4 py-2"><div className="ghost-cell w-32" style={{ animationDelay: `${rowIdx * 0.15}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-16 mx-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.05}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-12 mx-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.1}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-16 mx-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.15}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-10 mx-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.2}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-14 ml-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.25}s` }} /></td>
                    <td className="px-3 py-2"><div className="ghost-cell w-12 mx-auto" style={{ animationDelay: `${rowIdx * 0.15 + 0.3}s` }} /></td>
                    <td className="px-3 py-2" />
                  </tr>
                ))}
                {/* Terminal log overlay */}
                <tr>
                  <td colSpan={8} className="px-4 py-3 bg-white/[0.01]">
                    <div className="font-[family-name:var(--font-mono)] text-[9px] space-y-1">
                      <div className="text-emerald-500"><span className="text-zinc-600">&gt;</span> Fetching Territory Data... <span className="text-emerald-500 font-black">[OK]</span></div>
                      <div className="text-amber-500"><span className="text-zinc-600">&gt;</span> Calculating Health Metrics... <span className="text-amber-500 font-black animate-pulse">[RUNNING]</span></div>
                      <div className="text-zinc-600"><span className="text-zinc-700">&gt;</span> Building Pipeline Index... <span className="text-zinc-600">[ QUEUED ]</span></div>
                    </div>
                  </td>
                </tr>
              </>
            ) : processedAccounts.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-16 text-zinc-700 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.2em]">
                  No records match filter criteria
                </td>
              </tr>
            ) : (
              processedAccounts.map((acc, idx) => (
                <motion.tr
                  layout
                  key={acc.Account_ID}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ 
                    height: '44px',
                    z: 5,
                    boxShadow: '0 0 20px rgba(37,99,235,0.4), inset 0 0 20px rgba(37,99,235,0.05)',
                    backgroundColor: 'rgba(37,99,235,0.05)'
                  }}
                  transition={{ duration: 0.2, ease: 'easeOut' }}
                  onClick={() => onAccountClick(acc)}
                  className="border-b border-white/[0.02] cursor-pointer group relative"
                  style={{ height: '36px', transformStyle: 'preserve-3d' }}
                >
                  <td className="px-4 py-0 relative z-10">
                    <div className="flex flex-col justify-center">
                      <span className="font-bold text-foreground group-hover:text-primary transition-colors duration-150 text-[11px] leading-tight">{acc.Account_Name}</span>
                      <span className="text-[8px] text-zinc-700 font-[family-name:var(--font-mono)] uppercase tracking-[0.05em]">{acc.Account_ID}</span>
                    </div>
                  </td>
                  <td className="px-3 py-0 text-center relative z-10">
                    <span className="text-[9px] text-zinc-500 font-medium">{acc.Industry || '—'}</span>
                  </td>
                  <td className="px-3 py-0 text-center relative z-10">
                    <span className="text-[9px] text-zinc-500 font-[family-name:var(--font-mono)] uppercase tracking-wider">{acc.Territory || '—'}</span>
                  </td>
                  <td className="px-3 py-0 text-center relative z-10">
                    <span className={`inline-block px-2 py-0.5 rounded text-[8px] font-black uppercase border ${getTierStyle(acc.Account_Tier)}`}>
                      {acc.Account_Tier}
                    </span>
                  </td>
                  <td className="px-3 py-0 text-center relative z-10">
                    <div className="flex flex-col items-center gap-0.5">
                      <span className="text-[11px] font-black data-cell">{acc.health_score ?? '—'}</span>
                      <div className="w-10 h-[3px] bg-white/[0.04] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${getHealthColor(acc.health_score ?? 0)}`}
                          style={{ width: `${Math.min(acc.health_score ?? 0, 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-0 text-right relative z-10">
                    <span className="text-[11px] font-bold data-cell tabular-nums text-foreground">{formatCurrency(acc.total_pipeline_value)}</span>
                  </td>
                  <td className="px-3 py-0 text-center relative z-10">
                    <span className="text-[9px] text-zinc-600 font-[family-name:var(--font-mono)]">{getRelativeTime(acc.last_activity_date)}</span>
                  </td>
                  <td className="px-3 py-0 text-right relative z-10">
                    <div className="relative h-full flex items-center justify-end pr-2">
                       {/* Default icon */}
                       <MoreHorizontal className="w-3.5 h-3.5 text-zinc-700 group-hover:opacity-0 transition-opacity absolute right-4" />
                       
                       {/* Micro-actions overlay on hover */}
                       <div className="opacity-0 group-hover:opacity-100 flex items-center gap-2 transition-opacity absolute right-4">
                         <div className="p-1 hover:bg-white/[0.05] rounded text-zinc-400 hover:text-white transition-colors" data-tooltip="Edit">
                           <Edit className="w-3 h-3" />
                         </div>
                         <div className="p-1 hover:bg-white/[0.05] rounded text-emerald-500 hover:text-white transition-colors" data-tooltip="Signal">
                           <Terminal className="w-3 h-3" />
                         </div>
                         <div className="p-1 hover:bg-red-500/10 rounded text-red-500 transition-colors" data-tooltip="Flag Risk">
                           <Flag className="w-3 h-3" />
                         </div>
                       </div>
                    </div>
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
