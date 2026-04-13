'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatTerminal from '../components/ChatTerminal';
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
    // Use enriched endpoint for full data
    fetch('http://localhost:8001/api/accounts/enriched')
      .then(res => res.json())
      .then(data => {
        setAccounts(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to basic endpoint
        fetch('http://localhost:8001/api/accounts')
          .then(res => res.json())
          .then(data => {
            setAccounts(data || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, []);

  const handleAccountClick = (acc: any) => {
    setSelectedAccount(acc);
    setCommand(`Give me a detailed strategic health check on ${acc.Account_Name}`);
    setTimeout(() => setCommand(undefined), 500);
  };

  return (
    <div className="space-y-8">
      <AnimatePresence mode="wait">
        {selectedAccount ? (
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            className="grid grid-cols-1 xl:grid-cols-12 gap-6"
          >
            <div className="xl:col-span-8">
              <AccountDetail
                account={selectedAccount}
                onBack={() => setSelectedAccount(null)}
              />
            </div>
            <div className="xl:col-span-4 lg:sticky lg:top-6 h-fit">
              <div className="h-[700px]">
                <ChatTerminal externalCommand={command} />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="space-y-8"
          >
            <KPIGrid />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-8 space-y-6">
                <PipelineView />
                <PortfolioLedger
                  accounts={accounts}
                  loading={loading}
                  search={search}
                  onSearchChange={setSearch}
                  onAccountClick={handleAccountClick}
                />
              </div>

              <div className="lg:col-span-4 lg:sticky lg:top-6 h-fit">
                <div className="h-[700px]">
                  <ChatTerminal externalCommand={command} />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
