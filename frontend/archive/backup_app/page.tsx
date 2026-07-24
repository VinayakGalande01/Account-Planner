'use client';

// LEGACY/BACKUP FILE — not part of the active build (frontend/src is the live app).
// Original dashboard page: toggled between the KPI/Pipeline/Ledger overview and a
// single AccountDetail drill-down view based on selectedAccount from DataContext.
//
// --- SECTION: Imports & Data Hook ---
// --- SECTION: DashboardPage Component ---
//   - AnimatePresence switch: "detail" (AccountDetail) vs "dashboard" (KPI/Pipeline/Ledger)

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ChatTerminal from '../components/ChatTerminal';
import AccountDetail from '../components/AccountDetail';
import KPIGrid from '../components/KPIGrid';
import PipelineView from '../components/PipelineView';
import PortfolioLedger from '../components/PortfolioLedger';

import { useData } from '../context/DataContext';

export default function DashboardPage() {
  const { 
    accounts, 
    loading, 
    search, 
    setSearch, 
    selectedAccount, 
    setSelectedAccount 
  } = useData();

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

            <div className="grid grid-cols-1 gap-8">
              <div className="w-full space-y-8">
                <PipelineView />
                <PortfolioLedger
                  accounts={accounts}
                  loading={loading}
                  search={search}
                  onSearchChange={setSearch}
                  onAccountClick={(acc) => setSelectedAccount(acc)}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
