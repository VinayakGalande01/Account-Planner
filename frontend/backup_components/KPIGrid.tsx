'use client';

import React, { useState, useEffect } from 'react';
import { Zap, PieChart, ShieldAlert, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { motion } from 'framer-motion';

interface KPIData {
  label: string;
  value: string;
  change: string;
  changeType: 'up' | 'down' | 'neutral';
  icon: React.ElementType;
  iconColor: string;
}

const staticKPIs: KPIData[] = [
  { label: 'Global Health', value: '84%', change: '+2.4%', changeType: 'up', icon: Zap, iconColor: 'text-emerald-500' },
  { label: 'Pipeline Value', value: '$12.4M', change: '+12%', changeType: 'up', icon: PieChart, iconColor: 'text-primary' },
  { label: 'Risk of Client Loss', value: '04', change: '$210K', changeType: 'down', icon: ShieldAlert, iconColor: 'text-red-500' },
  { label: 'AI Usage', value: '92%', change: 'ACTIVE', changeType: 'neutral', icon: Activity, iconColor: 'text-secondary' },
];

export default function KPIGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {staticKPIs.map((kpi, idx) => {
        const Icon = kpi.icon;
        return (
          <motion.div
            key={kpi.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: idx * 0.08, ease: 'easeOut' }}
            className="corner-brackets bg-card p-5 hover:scale-[1.01] hover:shadow-[inset_0_0_20px_rgba(37,99,235,0.03)] transition-all duration-200 cursor-default group"
          >
            <div className="flex justify-between items-start mb-3">
              <p className="text-[12px] font-black uppercase text-zinc-600 dark:text-zinc-500 tracking-[0.12em] font-[family-name:var(--font-mono)]">
                {kpi.label}
              </p>
              <div className="p-1 bg-muted rounded">
                <Icon className={`w-3 h-3 ${kpi.iconColor}`} />
              </div>
            </div>
            <div className="flex items-end justify-between">
              <p className="text-2xl font-black text-foreground data-cell">{kpi.value}</p>
              <div className={`flex items-center gap-1 text-[13px] font-bold ${
                kpi.changeType === 'up' ? 'text-emerald-500/70 drop-shadow-[0_0_4px_rgba(16,185,129,0.15)]' :
                kpi.changeType === 'down' ? 'text-red-500/70 drop-shadow-[0_0_4px_rgba(239,68,68,0.15)]' :
                'text-secondary/60'
              }`}>
                {kpi.changeType === 'up' && <ArrowUpRight className="w-3 h-3" />}
                {kpi.changeType === 'down' && <ArrowDownRight className="w-3 h-3" />}
                <span className="font-[family-name:var(--font-mono)]">{kpi.change}</span>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
