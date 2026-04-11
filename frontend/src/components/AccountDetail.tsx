'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, Activity, Users, DollarSign, Target, 
  TrendingUp, AlertCircle, Building2, Briefcase, 
  Mail, Phone, ExternalLink, ShieldCheck, Download, 
  Settings, History, Globe, Database
} from 'lucide-react';
import PipelineChart from './PipelineChart';

interface AccountDetailProps {
  account: any;
  onBack: () => void;
}

export default function AccountDetail({ account, onBack }: AccountDetailProps) {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-8 pb-10"
    >
      {/* ERP Header Bar */}
      <div className="flex items-center justify-between border-b border-white/5 pb-6">
        <div className="flex items-center gap-6">
          <button 
            onClick={onBack}
            className="p-2 hover:bg-white/5 rounded-lg border border-white/5 transition-all text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="h-8 w-px bg-white/5 mx-2 hidden sm:block"></div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black text-foreground tracking-tight uppercase">{account.Account_Name}</h1>
              <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border ${
                 account.Account_Tier === 'Strategic' 
                  ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' 
                  : 'bg-blue-500/10 border-blue-500/20 text-blue-500'
              }`}>
                 {account.Account_Tier}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1">
               <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                  <Globe className="w-3 h-3" /> HQ: Mumbai, India
               </span>
               <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                  <Database className="w-3 h-3" /> ID: {account.Account_ID}
               </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
           <button className="px-4 py-2 bg-white/5 text-muted-foreground text-[10px] font-black rounded uppercase border border-white/5 hover:bg-white/10 transition-all flex items-center gap-2">
              <Download className="w-3.5 h-3.5" /> Export Data
           </button>
           <button className="px-4 py-2 bg-primary text-primary-foreground text-[10px] font-black rounded uppercase shadow-lg shadow-primary/20 hover:scale-105 transition-all flex items-center gap-2">
              <TrendingUp className="w-3.5 h-3.5" /> Strategic Report
           </button>
        </div>
      </div>

      {/* Main ERP-View Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Widget: Health Stats */}
        <div className="bg-card border border-white/5 p-6 rounded-lg space-y-6">
           <div>
              <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-4">Relational Health Index</p>
              <div className="flex items-center justify-between">
                 <div className="relative w-24 h-24 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                       <circle cx="48" cy="48" r="42" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-white/5" />
                       <circle cx="48" cy="48" r="42" stroke="currentColor" strokeWidth="6" fill="transparent" strokeDasharray={264} strokeDashoffset={264 * (1 - 0.84)} className="text-emerald-500" />
                    </svg>
                    <span className="absolute text-2xl font-black text-foreground">84</span>
                 </div>
                 <div className="space-y-3">
                    <div className="flex items-center gap-2">
                       <div className="w-2 h-2 rounded-sm bg-emerald-500"></div>
                       <span className="text-[10px] font-bold text-foreground">Sentiment: Positive</span>
                    </div>
                    <div className="flex items-center gap-2">
                       <div className="w-2 h-2 rounded-sm bg-amber-500"></div>
                       <span className="text-[10px] font-bold text-foreground">Engagement: High</span>
                    </div>
                    <div className="flex items-center gap-2">
                       <div className="w-2 h-2 rounded-sm bg-primary"></div>
                       <span className="text-[10px] font-bold text-foreground">Next Event: QBR (12d)</span>
                    </div>
                 </div>
              </div>
           </div>
           <div className="pt-4 border-t border-white/5">
              <p className="text-[10px] font-black text-rose-500 uppercase tracking-[0.2em] mb-4">Active Risks</p>
              <div className="space-y-2">
                 <div className="p-3 bg-rose-500/5 border border-rose-500/10 rounded-lg">
                    <p className="text-[10px] font-black text-foreground">Competitor Contract Expiry (Dec 2026)</p>
                    <p className="text-[9px] text-muted-foreground mt-1 leading-relaxed italic">Immediate outreach required to lock in renewal terms.</p>
                 </div>
              </div>
           </div>
        </div>

        {/* Center Widget: Revenue & Performance */}
        <div className="lg:col-span-2 bg-card border border-white/5 p-6 rounded-lg space-y-6">
           <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Revenue Forecast & Velocity</p>
              <div className="flex gap-4">
                 <div className="text-right">
                    <p className="text-sm font-black text-foreground">$450M</p>
                    <p className="text-[8px] text-muted-foreground font-black uppercase">ACV Portfolio</p>
                 </div>
                 <div className="text-right">
                    <p className="text-sm font-black text-emerald-500">+14%</p>
                    <p className="text-[8px] text-muted-foreground font-black uppercase">Growth Rate</p>
                 </div>
              </div>
           </div>
           <div className="h-64 pt-2">
              <PipelineChart />
           </div>
        </div>

        {/* Bottom Widgets Floor */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
           {/* Detailed Data Table for Opportunities */}
           <div className="md:col-span-2 bg-card border border-white/5 rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5 bg-white/[0.02]">
                 <h4 className="text-[10px] font-black uppercase text-foreground tracking-widest">Active Opportunity Pipeline</h4>
              </div>
              <table className="w-full text-left text-[11px]">
                 <thead>
                    <tr className="border-b border-white/5 bg-white/[0.01]">
                       <th className="px-6 py-3 font-bold text-muted-foreground uppercase tracking-tighter">Deal Name</th>
                       <th className="px-6 py-3 font-bold text-muted-foreground uppercase tracking-tighter text-center">Stage</th>
                       <th className="px-6 py-3 font-bold text-muted-foreground uppercase tracking-tighter text-right">Value</th>
                    </tr>
                 </thead>
                 <tbody>
                    {[
                      { name: 'Global Cloud Migration', stage: 'Contracting', value: '$2.5M' },
                      { name: 'Cybersecurity Suite Upgrade', stage: 'Negotiation', value: '$1.2M' },
                      { name: 'Data Lake Pilot', stage: 'Discovery', value: '$450K' }
                    ].map((deal, i) => (
                      <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                         <td className="px-6 py-3 font-bold">{deal.name}</td>
                         <td className="px-6 py-3 text-center">
                            <span className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[9px] uppercase font-bold text-muted-foreground">
                               {deal.stage}
                            </span>
                         </td>
                         <td className="px-6 py-3 text-right font-black text-primary">{deal.value}</td>
                      </tr>
                    ))}
                 </tbody>
              </table>
           </div>

           {/* Contact Matrix */}
           <div className="bg-card border border-white/5 rounded-lg overflow-hidden shrink-0">
              <div className="px-6 py-4 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                 <h4 className="text-[10px] font-black uppercase text-foreground tracking-widest">Key Contacts</h4>
                 <Users className="w-3 h-3 text-muted-foreground" />
              </div>
              <div className="p-4 space-y-4">
                 {[1, 2].map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                       <div className="w-8 h-8 rounded bg-white/5 border border-white/10 flex items-center justify-center font-black text-[10px] text-muted-foreground">JS</div>
                       <div className="flex-1 min-w-0">
                          <p className="text-[11px] font-bold truncate">John Smith</p>
                          <p className="text-[9px] text-muted-foreground truncate font-medium">Chief Technology Officer</p>
                       </div>
                       <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" title="Highly Engaged"></div>
                    </div>
                 ))}
                 <button className="w-full py-2 bg-white/5 hover:bg-white/10 text-[9px] font-black uppercase rounded border border-white/5 transition-all text-muted-foreground">View Directory</button>
              </div>
           </div>
        </div>
      </div>
    </motion.div>
  );
}
