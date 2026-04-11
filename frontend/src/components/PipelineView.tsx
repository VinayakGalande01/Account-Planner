'use client';

import React from 'react';
import { BarChart3 } from 'lucide-react';
import PipelineChart from './PipelineChart';

export default function PipelineView() {
  return (
    <div className="bg-card border border-white/5 rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
        <h3 className="text-[11px] font-black uppercase tracking-widest text-foreground flex items-center gap-2">
           <BarChart3 className="w-3.5 h-3.5 text-primary" />
           Revenue Velocity Projection
        </h3>
        <div className="flex gap-4 text-[10px] font-bold text-muted-foreground">
           <span className="text-primary border-b border-primary">6-Month</span>
           <span className="hover:text-foreground cursor-pointer">1-Year</span>
        </div>
      </div>
      <div className="p-8">
        <PipelineChart />
      </div>
    </div>
  );
}
