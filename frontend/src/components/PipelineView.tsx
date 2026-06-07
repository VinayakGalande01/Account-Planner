'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown, Sliders, CheckCircle2 } from 'lucide-react';

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
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

// Forecasted vs Actual vs Simulated — thin step-line SVG
interface StepLineChartProps {
  forecasted: number[];
  actual: number[];
  simulated: number[];
}

function StepLineChart({ forecasted, actual, simulated }: StepLineChartProps) {
  const maxVal = Math.max(...forecasted, ...actual, ...simulated, 1);
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
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-24" preserveAspectRatio="none">
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map(f => (
        <line key={f} x1={padding} x2={w - padding} y1={padding + usableH * (1 - f)} y2={padding + usableH * (1 - f)} stroke="var(--color-border)" strokeWidth="0.3" opacity="0.3" />
      ))}
      
      {/* Forecasted — dashed cobalt */}
      <path d={toPath(forecasted)} fill="none" stroke="#2563eb" strokeWidth="0.8" strokeDasharray="2 1.5" strokeLinecap="round" />
      
      {/* Simulated — glowing violet */}
      <path d={toPath(simulated)} fill="none" stroke="#7c3aed" strokeWidth="1.2" strokeLinecap="round" className="drop-shadow-[0_0_3px_rgba(124,58,237,0.8)]" />
      
      {/* Actual — solid white */}
      <path d={toPath(actual)} fill="none" stroke="currentColor" strokeWidth="0.8" strokeLinecap="round" className="text-foreground" />
    </svg>
  );
}

// Segmented progress bar for a single pipeline stage (shows actual + simulated delta overlay)
function SegmentedBar({ label, value, maxValue, color, simMultiplier }: { label: string; value: number; maxValue: number; color: string; simMultiplier: number }) {
  const actualPct = maxValue > 0 ? (value / maxValue) * 100 : 0;
  const simValue = value * simMultiplier;
  const simPct = maxValue > 0 ? (simValue / maxValue) * 100 : 0;

  return (
    <div className="flex items-center gap-3 group">
      <span className="text-[12px] font-bold text-zinc-600 w-28 text-right shrink-0 font-[family-name:var(--font-mono)] uppercase tracking-[0.05em] group-hover:text-zinc-400 transition-colors truncate">
        {label}
      </span>
      <div className="flex-1 h-[6px] bg-muted rounded-sm overflow-hidden relative">
        {/* Simulated shadow */}
        <div
          className="h-full rounded-sm absolute left-0 top-0 opacity-30 transition-all duration-300 ease-out"
          style={{ width: `${Math.min(simPct, 100)}%`, backgroundColor: '#7c3aed' }}
        />
        {/* Actual */}
        <div
          className="h-full rounded-sm absolute left-0 top-0 transition-all duration-500 ease-out"
          style={{ width: `${Math.min(actualPct, 100)}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[13px] font-bold text-zinc-400 w-16 text-right shrink-0 data-cell font-[family-name:var(--font-mono)]">
        {formatCurrency(value)}
      </span>
      <span className={`text-[12px] font-bold w-14 text-right shrink-0 font-[family-name:var(--font-mono)] ${simValue >= value ? 'text-secondary' : 'text-red-500/70'}`}>
        {simValue !== value && `→ ${formatCurrency(simValue)}`}
      </span>
    </div>
  );
}

export default function PipelineView() {
  const [pipelineData, setPipelineData] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  // What-If Simulator States
  const [winRateBoost, setWinRateBoost] = useState(0); // in percent (-20% to +30%)
  const [dealSizeExpansion, setDealSizeExpansion] = useState(1.0); // multiplier (0.5 to 2.0)
  const [cycleAcceleration, setCycleAcceleration] = useState(0); // in percent (0% to 50%)

  useEffect(() => {
    fetch('http://127.0.0.1:8002/api/pipeline/summary')
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

  const totalPipeline = Object.entries(pipelineData)
    .filter(([k]) => k !== 'Closed Won' && k !== 'Closed Lost')
    .reduce((sum, [, v]) => sum + v, 0);
  const closedWon = pipelineData['Closed Won'] || 0;

  // Recalculate based on sliders
  // Win rate boost shifts opportunities to Closed Won. Expansion multiplies overall deal size. Cycle acceleration speeds up early stages into Won.
  const simTotalPipeline = totalPipeline * dealSizeExpansion * (1 - cycleAcceleration * 0.005);
  const simClosedWon = closedWon + (totalPipeline * (0.15 + winRateBoost / 100) * dealSizeExpansion * (1 + cycleAcceleration * 0.012));

  // Original Forecasted vs Actual data
  const baseForecasted = [2.1, 2.4, 2.8, 3.1, 3.6, 4.0, 4.2]; // In Millions
  const actual = [1.8, 2.2, 2.5, 2.9, 3.2, 3.4, 3.9]; // In Millions

  // Dynamic Simulated Forecast Trend line
  const simulatedForecast = baseForecasted.map(v => 
    v * dealSizeExpansion * (1 + (winRateBoost * 0.012) + (cycleAcceleration * 0.008))
  );

  const maxStageValue = Math.max(...Object.values(pipelineData), 1) * Math.max(1, dealSizeExpansion);

  // Generate dynamic commentary based on changes
  const getSimulationCommentary = () => {
    if (winRateBoost === 0 && dealSizeExpansion === 1 && cycleAcceleration === 0) {
      return "Simulator is idle. Adjust the sliders below to see different sales scenarios.";
    }
    const diff = simClosedWon - closedWon;
    const diffPct = ((diff / (closedWon || 1)) * 100).toFixed(1);
    if (diff > 0) {
      return `These settings predict a won sales increase of +${formatCurrency(diff)} (+${diffPct}%), speeding up your Q4 sales.`;
    } else {
      return `These settings predict a sales drop of -${formatCurrency(Math.abs(diff))} (-${Math.abs(Number(diffPct))}%). We suggest finding more leads to fill the gap.`;
    }
  };

  return (
    <div className="space-y-6">
      <div className="corner-brackets bg-card rounded-md overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-muted/30">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-3.5 h-3.5 text-primary" />
            <h3 className="text-[13px] font-black uppercase tracking-[0.15em] text-foreground font-[family-name:var(--font-mono)]">
              Sales Progress & Speed
            </h3>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-sm font-black text-foreground data-cell">{formatCurrency(totalPipeline)}</p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-500 font-black uppercase font-[family-name:var(--font-mono)]">Open Pipeline</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-black text-emerald-500 data-cell">{formatCurrency(closedWon)}</p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-500 font-black uppercase font-[family-name:var(--font-mono)]">Closed Won</p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-6">
          {/* Forecasted vs Actual vs Simulated Step-Line */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[12px] font-bold text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.12em] font-[family-name:var(--font-mono)]">
                Sales Speed: Actual vs. Simulation
              </span>
              <div className="flex items-center gap-4 text-[12px] font-[family-name:var(--font-mono)]">
                <span className="flex items-center gap-1.5">
                  <span className="w-4 h-[1px] border-t border-dashed border-blue-500 inline-block" />
                  <span className="text-zinc-600 dark:text-zinc-500">Forecast</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-4 h-[1.2px] bg-secondary inline-block" />
                  <span className="text-zinc-600 dark:text-zinc-500">Simulation</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-4 h-[1px] bg-foreground inline-block" />
                  <span className="text-zinc-600 dark:text-zinc-500">Actual</span>
                </span>
              </div>
            </div>
            <div className="bg-muted/30 rounded p-3 border border-border">
              <StepLineChart forecasted={baseForecasted} actual={actual} simulated={simulatedForecast} />
            </div>
          </div>

          {/* Segmented Stage Bars */}
          <div>
            <span className="text-[12px] font-bold text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.12em] font-[family-name:var(--font-mono)] mb-3 block">
              Sales Stages (Current vs. Simulated)
            </span>
            {loading ? (
              <div className="py-8 text-center text-[13px] text-zinc-700 font-[family-name:var(--font-mono)] uppercase tracking-widest">
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
                    simMultiplier={stage === 'Closed Won' ? 1.0 : dealSizeExpansion}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Interactive What-If Simulator Panel */}
      <div className="corner-brackets bg-card rounded-md overflow-hidden">
        <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sliders className="w-3.5 h-3.5 text-secondary animate-pulse" />
            <h3 className="text-[13px] font-black uppercase tracking-[0.15em] text-secondary font-[family-name:var(--font-mono)]">
              Sales Simulation Levers
            </h3>
          </div>
          {(winRateBoost !== 0 || dealSizeExpansion !== 1.0 || cycleAcceleration !== 0) && (
            <button 
              onClick={() => {
                setWinRateBoost(0);
                setDealSizeExpansion(1.0);
                setCycleAcceleration(0);
              }}
              className="text-[11px] font-black text-zinc-500 hover:text-white uppercase tracking-widest font-[family-name:var(--font-mono)]"
            >
              Reset Levers
            </button>
          )}
        </div>

        <div className="p-5 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Lever 1: Win Rate Boost */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-[12px] font-[family-name:var(--font-mono)] uppercase">
                <span className="text-zinc-500 font-bold">Win Rate Boost</span>
                <span className={`font-black ${winRateBoost > 0 ? 'text-secondary' : winRateBoost < 0 ? 'text-red-500' : 'text-zinc-400'}`}>
                  {winRateBoost >= 0 ? `+${winRateBoost}%` : `${winRateBoost}%`}
                </span>
              </div>
              <input
                type="range"
                min="-15"
                max="25"
                value={winRateBoost}
                onChange={(e) => setWinRateBoost(parseInt(e.target.value))}
                className="w-full accent-secondary bg-muted h-[3px] rounded-lg cursor-pointer"
              />
              <p className="text-[11.5px] text-zinc-600 dark:text-zinc-500 leading-normal font-medium">
                Changes how likely we are to win open opportunities.
              </p>
            </div>

            {/* Lever 2: Deal Size Expansion */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-[12px] font-[family-name:var(--font-mono)] uppercase">
                <span className="text-zinc-500 font-bold">Deal Size Multiplier</span>
                <span className={`font-black ${dealSizeExpansion > 1.0 ? 'text-secondary' : dealSizeExpansion < 1.0 ? 'text-red-500' : 'text-zinc-400'}`}>
                  {dealSizeExpansion.toFixed(2)}x
                </span>
              </div>
              <input
                type="range"
                min="50"
                max="175"
                value={dealSizeExpansion * 100}
                onChange={(e) => setDealSizeExpansion(parseInt(e.target.value) / 100)}
                className="w-full accent-secondary bg-muted h-[3px] rounded-lg cursor-pointer"
              />
              <p className="text-[11.5px] text-zinc-600 dark:text-zinc-500 leading-normal font-medium">
                Simulates selling larger contracts or cross-selling to active clients.
              </p>
            </div>

            {/* Lever 3: Cycle Acceleration */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-[12px] font-[family-name:var(--font-mono)] uppercase">
                <span className="text-zinc-500 font-bold">Sales Cycle Speedup</span>
                <span className={`font-black ${cycleAcceleration > 0 ? 'text-secondary' : 'text-zinc-400'}`}>
                  +{cycleAcceleration}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="40"
                value={cycleAcceleration}
                onChange={(e) => setCycleAcceleration(parseInt(e.target.value))}
                className="w-full accent-secondary bg-muted h-[3px] rounded-lg cursor-pointer"
              />
              <p className="text-[11.5px] text-zinc-600 dark:text-zinc-500 leading-normal font-medium">
                Simulates moving early deals faster through the sales cycle.
              </p>
            </div>
          </div>

          {/* Results Summary Bar */}
          <div className="pt-4 border-t border-border flex flex-col md:flex-row justify-between items-start md:items-center gap-5">
            <div className="flex gap-6 shrink-0">
              <div>
                <span className="text-[11px] text-zinc-500 font-black uppercase font-[family-name:var(--font-mono)] tracking-wider">
                  Simulated Closed Won
                </span>
                <p className="text-base font-black text-secondary data-cell leading-tight mt-0.5">
                  {formatCurrency(simClosedWon)}
                  {simClosedWon !== closedWon && (
                    <span className={`text-[13px] font-bold ml-1.5 ${simClosedWon >= closedWon ? 'text-emerald-500' : 'text-red-500'}`}>
                      ({simClosedWon >= closedWon ? '+' : ''}{(((simClosedWon - closedWon) / (closedWon || 1)) * 100).toFixed(1)}%)
                    </span>
                  )}
                </p>
              </div>
              <div>
                <span className="text-[11px] text-zinc-500 font-black uppercase font-[family-name:var(--font-mono)] tracking-wider">
                  Simulated Open Pipe
                </span>
                <p className="text-base font-black text-zinc-400 data-cell leading-tight mt-0.5">
                  {formatCurrency(simTotalPipeline)}
                </p>
              </div>
            </div>

            <div className="flex-1 max-w-xl bg-muted/30 border border-border rounded p-3 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-[2px] h-full bg-secondary" />
              <p className="text-[13px] text-zinc-400 dark:text-zinc-300 font-medium leading-relaxed font-[family-name:var(--font-mono)]">
                <span className="font-black text-secondary uppercase tracking-widest block text-[11px] mb-0.5">AI Prediction</span>
                {getSimulationCommentary()}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
