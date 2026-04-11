'use client';

import React from 'react';
import { Zap, PieChart, ShieldAlert, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function KPIGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-6">
      <div className="bg-card border border-white/5 p-6 rounded-lg">
        <div className="flex justify-between items-start mb-4">
          <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Global Health</p>
          <div className="p-1 bg-emerald-500/10 rounded">
            <Zap className="w-3 h-3 text-emerald-500" />
          </div>
        </div>
        <div className="flex items-end justify-between">
          <p className="text-3xl font-black text-foreground">84%</p>
          <div className="flex items-center gap-1 text-emerald-500 text-[10px] font-bold">
            <ArrowUpRight className="w-3 h-3" /> 2.4%
          </div>
        </div>
      </div>
      <div className="bg-card border border-white/5 p-6 rounded-lg">
         <div className="flex justify-between items-start mb-4">
            <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Pipe Value</p>
            <PieChart className="w-3 h-3 text-primary" />
         </div>
         <div className="flex items-end justify-between">
            <p className="text-3xl font-black text-foreground">$12.4M</p>
            <div className="flex items-center gap-1 text-primary text-[10px] font-bold">
               <ArrowUpRight className="w-3 h-3" /> 12%
            </div>
         </div>
      </div>
      <div className="bg-card border border-white/5 p-6 rounded-lg">
         <div className="flex justify-between items-start mb-4">
            <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Churn Risk</p>
            <ShieldAlert className="w-3 h-3 text-rose-500" />
         </div>
         <div className="flex items-end justify-between">
            <p className="text-3xl font-black text-foreground">04</p>
            <div className="flex items-center gap-1 text-rose-500 text-[10px] font-bold">
               <ArrowDownRight className="w-3 h-3" /> $210K
            </div>
         </div>
      </div>
      <div className="bg-card border border-white/5 p-6 rounded-lg hidden lg:block">
         <div className="flex justify-between items-start mb-4">
            <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">AI Utilization</p>
            <Activity className="w-3 h-3 text-secondary" />
         </div>
         <div className="flex items-end justify-between">
            <p className="text-3xl font-black text-foreground">92%</p>
            <div className="flex items-center gap-1 text-secondary text-[10px] font-bold italic">
               PREMIUM
            </div>
         </div>
      </div>
    </div>
  );
}
