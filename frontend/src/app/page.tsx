'use client';

import React, { useState, useEffect } from 'react';
import { Search, ChevronRight, Activity, Zap, PieChart, ShieldAlert, BarChart3, Filter, MoreHorizontal, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatTerminal from '../components/ChatTerminal';
import PipelineChart from '../components/PipelineChart';
import AccountDetail from '../components/AccountDetail';

import KPIGrid from '../components/KPIGrid';
import PipelineView from '../components/PipelineView';
import PortfolioLedger from '../components/PortfolioLedger';

export default function Dashboard() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [command, setCommand] = useState<string | undefined>(undefined);
  const [selectedAccount, setSelectedAccount] = useState<any | null>(null);

  useEffect(() => {
    fetch('http://localhost:8001/api/accounts')
      .then(res => res.json())
      .then(data => {
        setAccounts(data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleAccountClick = (acc: any) => {
    setSelectedAccount(acc);
    setCommand(`Give me a detailed strategic health check on ${acc.Account_Name}`);
    setTimeout(() => setCommand(undefined), 500);
  };

  return (
    <div className="space-y-10">
      <AnimatePresence mode="wait">
        {selectedAccount ? (
          <motion.div 
            key="detail" 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="grid grid-cols-1 xl:grid-cols-12 gap-10"
          >
            <div className="xl:col-span-8">
              <AccountDetail 
                account={selectedAccount} 
                onBack={() => setSelectedAccount(null)} 
              />
            </div>
            <div className="xl:col-span-4 lg:sticky lg:top-8 h-fit">
              <ChatTerminal externalCommand={command} />
            </div>
          </motion.div>
        ) : (
          <motion.div 
            key="dashboard"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-10"
          >
            <KPIGrid />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
              <div className="lg:col-span-8 space-y-10">
                <PipelineView />
                <PortfolioLedger 
                  accounts={accounts}
                  loading={loading}
                  search={search}
                  onSearchChange={setSearch}
                  onAccountClick={handleAccountClick}
                />
              </div>

              <div className="lg:col-span-4 lg:sticky lg:top-8 h-fit">
                <ChatTerminal externalCommand={command} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
