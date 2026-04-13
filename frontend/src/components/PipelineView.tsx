'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown } from 'lucide-react';

// Pipeline stages in order
const STAGES = [
  'Prospecting',
  'Qualification',
  'Needs Analysis',
  'Value Proposition',
  'Id. Decision Makers',
  'Perception Analysis',
  'Proposal/Price Quote',
  'Negotiation/Review',
  'Closed Won',
  'Closed Lost',
];

// Stage colors — cool→hot gradient
const STAGE_COLORS: Record<string, string> = {
  'Prospecting': '#3b82f6',
  'Qualification': '#6366f1',
  'Needs Analysis': '#8b5cf6',
  'Value Proposition': '#a855f7',
  'Id. Decision Makers': '#d946ef',
  'Perception Analysis': '#ec4899',
  'Proposal/Price Quote': '#f59e0b',
  'Negotiation/Review': '#ef4444',
  'Closed Won': '#10b981',
  'Closed Lost': '#52525b',
};

function formatCurrency(val: number): string {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

// Forecasted vs Actual — thin step-line SVG
function StepLineChart({ forecasted, actual }: { forecasted: number[]; actual: number[] }) {
  const maxVal = Math.max(...forecasted, ...actual, 1);
  const w = 100;
  const h = 40;
  const padding = 2;
  const usableW = w - padding * 2;
  const usableH = h - padding * 2;

  const toPath = (data: number[]) => {
    return data.map((v, i) => {
      const x = padding + (i / (data.length - 1)) * usableW;
      const y = padding + usableH - (v / maxVal) * usableH;
      return `${i === 0 ? 'M' : 'L'}${x},${y}`;
    }).join(' ');
  };

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" preserveAspectRatio="none">
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map(f => (
        <line key={f} x1={padding} x2={w - padding} y1={padding + usableH * (1 - f)} y2={padding + usableH * (1 - f)} stroke="rgba(255,255,255,0.03)" strokeWidth="0.3" />
      ))}
      {/* Forecasted — dashed cobalt */}
      <path d={toPath(forecasted)} fill="none" stroke="#2563eb" strokeWidth="0.8" strokeDasharray="2 1.5" strokeLinecap="round" />
      {/* Actual — solid white */}
      <path d={toPath(actual)} fill="none" stroke="#f4f4f5" strokeWidth="0.8" strokeLinecap="round" />
    </svg>
  );
}

// Segmented progress bar for a single pipeline stage
function SegmentedBar({ label, value, maxValue, color }: { label: string; value: number; maxValue: number; color: string }) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;

  return (
    <div className="flex items-center gap-3 group">
      <span className="text-[9px] font-bold text-zinc-600 w-28 text-right shrink-0 font-[family-name:var(--font-mono)] uppercase tracking-[0.05em] group-hover:text-zinc-400 transition-colors truncate">
        {label}
      </span>
      <div className="flex-1 h-[6px] bg-white/[0.03] rounded-sm overflow-hidden relative">
        <div
          className="h-full rounded-sm transition-all duration-700 ease-out"
          style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] font-bold text-zinc-400 w-16 text-right shrink-0 data-cell font-[family-name:var(--font-mono)]">
        {formatCurrency(value)}
      </span>
    </div>
  );
}

export default function PipelineView() {
  const [pipelineData, setPipelineData] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8001/api/pipeline/summary')
      .then(res => res.json())
      .then(data => {
        setPipelineData(data.stage_summary || {});
        setLoading(false);
      })
      .catch(() => {
        // Fallback mock data
        setPipelineData({
          'Prospecting': 1200000,
          'Qualification': 890000,
          'Needs Analysis': 650000,
          'Value Proposition': 420000,
          'Id. Decision Makers': 380000,
          'Proposal/Price Quote': 920000,
          'Negotiation/Review': 1100000,
          'Closed Won': 2400000,
          'Closed Lost': 310000,
        });
        setLoading(false);
      });
  }, []);

  const maxStageValue = Math.max(...Object.values(pipelineData), 1);
  const totalPipeline = Object.entries(pipelineData)
    .filter(([k]) => k !== 'Closed Won' && k !== 'Closed Lost')
    .reduce((sum, [, v]) => sum + v, 0);
  const closedWon = pipelineData['Closed Won'] || 0;

  // Mock forecasted vs actual data
  const forecasted = [2.1, 2.4, 2.8, 3.1, 3.6, 4.0, 4.2];
  const actual = [1.8, 2.2, 2.5, 2.9, 3.2, 3.4, 3.9];

  return (
    <div className="bg-[#080808] border border-white/[0.04] rounded-md overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between bg-white/[0.01]">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-3.5 h-3.5 text-primary" />
          <h3 className="text-[10px] font-black uppercase tracking-[0.15em] text-foreground font-[family-name:var(--font-mono)]">
            Pipeline Velocity
          </h3>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-sm font-black text-foreground data-cell">{formatCurrency(totalPipeline)}</p>
            <p className="text-[8px] text-zinc-600 font-black uppercase font-[family-name:var(--font-mono)]">Open Pipeline</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-black text-emerald-500 data-cell">{formatCurrency(closedWon)}</p>
            <p className="text-[8px] text-zinc-600 font-black uppercase font-[family-name:var(--font-mono)]">Closed Won</p>
          </div>
        </div>
      </div>

      <div className="p-5 space-y-6">
        {/* Forecasted vs Actual Step-Line */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-[0.12em] font-[family-name:var(--font-mono)]">
              Velocity: Forecasted vs Actual
            </span>
            <div className="flex items-center gap-4 text-[9px] font-[family-name:var(--font-mono)]">
              <span className="flex items-center gap-1.5">
                <span className="w-4 h-[1px] bg-blue-500 inline-block" style={{ borderTop: '1px dashed #2563eb' }} />
                <span className="text-zinc-600">Forecast</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-4 h-[1px] bg-foreground inline-block" />
                <span className="text-zinc-600">Actual</span>
              </span>
            </div>
          </div>
          <div className="bg-white/[0.01] rounded p-3 border border-white/[0.03]">
            <StepLineChart forecasted={forecasted} actual={actual} />
          </div>
        </div>

        {/* Segmented Stage Bars */}
        <div>
          <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-[0.12em] font-[family-name:var(--font-mono)] mb-3 block">
            Stage Distribution
          </span>
          {loading ? (
            <div className="py-8 text-center text-[10px] text-zinc-700 font-[family-name:var(--font-mono)] uppercase tracking-widest">
              Loading pipeline data...
            </div>
          ) : (
            <div className="space-y-2">
              {STAGES.filter(s => pipelineData[s] !== undefined).map(stage => (
                <SegmentedBar
                  key={stage}
                  label={stage}
                  value={pipelineData[stage] || 0}
                  maxValue={maxStageValue}
                  color={STAGE_COLORS[stage] || '#52525b'}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
