'use client'

import { motion } from 'framer-motion'
import { useState, useMemo } from 'react'
import { useData } from '@/context/DataContext'
import { Sidebar } from '@/components/Sidebar'
import { Header } from '@/components/header'
import { AICopilotPanel } from '@/components/ai-copilot-panel'
import { Sparkles, Search, ChevronDown } from 'lucide-react'

const formatCurrency = (val: number | undefined): string => {
  if (!val && val !== 0) return '—'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

export default function AccountsPage() {
  const { accounts, loading } = useData()
  const [isCopilotOpen, setIsCopilotOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTier, setFilterTier] = useState('ALL TIERS')
  const [sortBy, setSortBy] = useState('name')

  const filteredAccounts = useMemo(() => {
    return accounts
      .filter(account => {
        const nameMatch = (account.Account_Name || '').toLowerCase().includes(searchTerm.toLowerCase())
        const industryMatch = (account.Industry || '').toLowerCase().includes(searchTerm.toLowerCase())
        const matchesSearch = nameMatch || industryMatch
        
        // Ensure case-insensitive or consistent matching for tier
        const accTier = (account.Account_Tier || '').toUpperCase()
        const targetTier = filterTier.toUpperCase()
        const matchesTier = filterTier === 'ALL TIERS' || accTier === targetTier
        
        return matchesSearch && matchesTier
      })
      .sort((a, b) => {
        if (sortBy === 'name') return (a.Account_Name || '').localeCompare(b.Account_Name || '')
        if (sortBy === 'health') return (b.health_score || 0) - (a.health_score || 0)
        if (sortBy === 'pipeline') {
          return (b.total_pipeline_value || 0) - (a.total_pipeline_value || 0)
        }
        return 0
      })
  }, [accounts, searchTerm, filterTier, sortBy])

  const getTierBadgeColor = (tier: string) => {
    const colors: Record<string, string> = {
      'KEY': 'bg-primary/15 text-primary',
      'STRATEGIC': 'bg-chart-3/15 text-chart-3',
      'NORMAL': 'bg-muted/15 text-muted-foreground',
    }
    return colors[tier] || colors['NORMAL']
  }

  const getHealthColor = (health: number) => {
    if (health >= 30) return 'text-chart-2'
    if (health >= 20) return 'text-chart-3'
    return 'text-destructive'
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Header />

        <main className="flex-1 overflow-y-auto">
          <div className="p-6 md:p-8">
            {/* Page title */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-6"
            >
              <h1 className="text-3xl font-semibold text-foreground">Accounts</h1>
              <p className="text-sm text-muted-foreground mt-1">Account Directory - {accounts.length} records</p>
            </motion.div>

            {/* Filters and search */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="flex flex-col md:flex-row gap-3 mb-6 items-start md:items-center justify-between"
            >
              <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
                {/* Search */}
                <div className="relative flex-1 sm:flex-none">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter accounts..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-secondary border border-border rounded-md pl-9 pr-4 py-1.5 text-sm placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors"
                  />
                </div>

                {/* Tier filter */}
                <div className="relative">
                  <button className="flex items-center gap-2 px-3 py-1.5 bg-secondary border border-border rounded-md text-sm text-foreground hover:bg-secondary/50 transition-colors">
                    {filterTier}
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="text-sm text-muted-foreground">
                Showing {filteredAccounts.length} of {accounts.length}
              </div>
            </motion.div>

            {/* Accounts table */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15, duration: 0.4 }}
              className="bg-card border border-border rounded-lg overflow-hidden"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-secondary/10">
                      <th className="px-4 py-3 text-left font-semibold text-foreground cursor-pointer hover:bg-secondary/20" onClick={() => setSortBy('name')}>
                        Account
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground">Industry</th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground">Territory</th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground">Tier</th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground cursor-pointer hover:bg-secondary/20" onClick={() => setSortBy('health')}>
                        Health
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground cursor-pointer hover:bg-secondary/20" onClick={() => setSortBy('pipeline')}>
                        Pipeline
                      </th>
                      <th className="px-4 py-3 text-left font-semibold text-foreground">Last Activity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">Loading accounts...</td>
                      </tr>
                    ) : filteredAccounts.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">No accounts found.</td>
                      </tr>
                    ) : (
                      filteredAccounts.map((account, index) => (
                        <motion.tr
                          key={account.Account_ID || index}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 0.15 + index * 0.02 }}
                          className="border-b border-border hover:bg-secondary/10 transition-colors"
                        >
                          <td className="px-4 py-3 font-medium text-foreground">{account.Account_Name || 'Unknown'}</td>
                          <td className="px-4 py-3 text-muted-foreground">{account.Industry || '—'}</td>
                          <td className="px-4 py-3 text-muted-foreground text-xs uppercase">{account.Territory || '—'}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-sm text-xs font-medium ${getTierBadgeColor(account.Account_Tier?.toUpperCase() || 'NORMAL')}`}>
                              {account.Account_Tier?.toUpperCase() || 'NORMAL'}
                            </span>
                          </td>
                          <td className={`px-4 py-3 font-medium ${getHealthColor(account.health_score || 0)}`}>
                            {account.health_score || 0}
                          </td>
                          <td className="px-4 py-3 font-medium text-foreground">{formatCurrency(account.total_pipeline_value)}</td>
                          <td className="px-4 py-3 text-muted-foreground text-xs">{account.last_activity_date || 'N/A'}</td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </div>
        </main>
      </div>

      {/* Copilot button */}
      <motion.button
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.3 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsCopilotOpen(true)}
        className="fixed bottom-6 right-6 md:bottom-8 md:right-8 w-12 h-12 bg-primary rounded-lg flex items-center justify-center shadow-md hover:shadow-lg hover:bg-primary/90 transition-all z-30"
      >
        <Sparkles className="w-5 h-5 text-primary-foreground" />
      </motion.button>

      <AICopilotPanel isOpen={isCopilotOpen} onClose={() => setIsCopilotOpen(false)} />
    </div>
  )
}
