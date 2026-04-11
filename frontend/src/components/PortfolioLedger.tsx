'use client';

import React from 'react';
import { Search, Filter, MoreHorizontal } from 'lucide-react';

interface PortfolioLedgerProps {
  accounts: any[];
  loading: boolean;
  search: string;
  onSearchChange: (val: string) => void;
  onAccountClick: (acc: any) => void;
}

export default function PortfolioLedger({ accounts, loading, search, onSearchChange, onAccountClick }: PortfolioLedgerProps) {
  const filteredAccounts = accounts.filter(acc => 
    acc.Account_Name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-card border border-white/5 rounded-lg overflow-hidden">
       <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-4">
             <h3 className="text-[11px] font-black uppercase tracking-widest text-foreground">Portfolio Ledger</h3>
             <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                <input 
                   value={search}
                   onChange={(e) => onSearchChange(e.target.value)}
                   placeholder="Filter accounts..." 
                   className="bg-muted/30 border border-white/5 rounded pl-8 pr-3 py-1.5 text-[10px] focus:outline-none focus:border-primary/50"
                />
             </div>
          </div>
          <div className="flex gap-2">
             <button className="p-1.5 bg-white/5 rounded hover:bg-white/10 text-muted-foreground transition-all">
                <Filter className="w-3 h-3" />
             </button>
          </div>
       </div>
       <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px] border-collapse">
             <thead>
                <tr className="border-b border-white/5 bg-white/[0.01]">
                   <th className="px-6 py-3 font-black uppercase text-muted-foreground tracking-tighter">Account Name</th>
                   <th className="px-6 py-3 font-black uppercase text-muted-foreground tracking-tighter text-center">Tier</th>
                   <th className="px-6 py-3 font-black uppercase text-muted-foreground tracking-tighter text-center">Score</th>
                   <th className="px-6 py-3 font-black uppercase text-muted-foreground tracking-tighter text-right">Owner</th>
                   <th className="px-6 py-3"></th>
                </tr>
             </thead>
             <tbody>
                {loading ? (
                   <tr><td colSpan={5} className="text-center py-20 opacity-30 italic">Synchronizing with ERP Core...</td></tr>
                ) : (
                   filteredAccounts.map((acc, idx) => (
                      <tr 
                        key={acc.Account_ID} 
                        onClick={() => onAccountClick(acc)}
                        className="border-b border-white/[0.02] hover:bg-primary/[0.03] transition-colors cursor-pointer group"
                      >
                         <td className="px-6 py-4">
                            <div className="flex flex-col">
                               <span className="font-bold text-foreground group-hover:text-primary transition-colors">{acc.Account_Name}</span>
                               <span className="text-[9px] text-muted-foreground font-medium uppercase tracking-tighter">ID: {acc.Account_ID}</span>
                            </div>
                         </td>
                         <td className="px-6 py-4 text-center">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border ${
                               acc.Account_Tier === 'Strategic' 
                                ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' 
                                : 'bg-blue-500/10 border-blue-500/20 text-blue-500'
                            }`}>
                               {acc.Account_Tier}
                            </span>
                         </td>
                         <td className="px-6 py-4 text-center font-black">
                            <div className="flex flex-col items-center gap-1">
                               <span>84</span>
                               <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                                  <div className="h-full bg-emerald-500 w-[84%]"></div>
                               </div>
                            </div>
                         </td>
                         <td className="px-6 py-4 text-right font-medium text-muted-foreground">SENIOR AE</td>
                         <td className="px-6 py-4 text-right">
                            <MoreHorizontal className="w-3.5 h-3.5 opacity-30 group-hover:opacity-100" />
                         </td>
                      </tr>
                   ))
                )}
             </tbody>
          </table>
       </div>
    </div>
  );
}
