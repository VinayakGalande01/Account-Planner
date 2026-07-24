'use client'

/**
 * CRM ACCOUNTS PAGE (accounts/page.tsx)
 * Displays list matrices of CRM customer accounts with tier tags,
 * pipeline health metrics, ARR sums, and sorting/filtering toolbars.
 */

// --- SECTION 1: Dependencies & Utility Helpers ---
// Imports animation components, data contexts, and currency formatter functions.
import { motion } from 'framer-motion'
import { useState, useMemo } from 'react'
import { useData } from '@/context/DataContext'
import { Search, ChevronDown, Briefcase } from 'lucide-react'
import { useAnimation } from '@/context/AnimationContext'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/PageHeader'

const formatCurrency = (val: number | undefined): string => {
  if (!val && val !== 0) return '—'
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

export default function AccountsPage() {
  const { accounts, loading } = useData()
  const { isFirstVisit } = useAnimation()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTier, setFilterTier] = useState('ALL TIERS')
  const [sortBy, setSortBy] = useState('name')

  // --- SECTION: Filtering/Sorting Logic ---
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

  // --- SECTION: Badge/Color Helpers ---
  const getTierBadgeColor = (tier: string) => {
    const colors: Record<string, string> = {
      'KEY': 'bg-primary/15 text-primary',
      'STRATEGIC': 'bg-chart-3/15 text-chart-3',
      'NORMAL': 'bg-muted/15 text-muted-foreground',
    }
    return colors[tier] || colors['NORMAL']
  }

  const getHealthColor = (health: number) => {
    if (health >= 70) return 'text-emerald-400 font-semibold'
    if (health >= 40) return 'text-amber-400 font-semibold'
    return 'text-red-400 font-semibold'
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8">
        <PageHeader
          title="Accounts"
          subtitle={`Account Directory - ${accounts.length} records`}
          icon={<Briefcase className="w-6 h-6" />}
        />

        {/* --- SECTION: Render - Filters Toolbar --- */}
        {/* Filters and search */}
        <motion.div
          initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: isFirstVisit ? 0.1 : 0, duration: 0.4 }}
          className="flex flex-col md:flex-row gap-3 mb-6 items-start md:items-center justify-between"
        >
          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            {/* Search */}
            <div className="relative flex-1 sm:flex-none">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" aria-hidden="true" />
              <input
                type="text"
                placeholder="Filter accounts..."
                aria-label="Filter accounts by name or industry"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-secondary border border-border rounded-md pl-9 pr-4 py-1.5 text-sm placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors"
              />
            </div>

            {/* Tier filter */}
            <div className="relative">
              <select
                value={filterTier}
                onChange={(e) => setFilterTier(e.target.value)}
                aria-label="Filter accounts by tier"
                className="px-3 py-1.5 bg-secondary border border-border rounded-md text-sm text-foreground hover:bg-secondary/50 focus:outline-none focus:ring-1 focus:ring-primary transition-colors appearance-none pr-8 cursor-pointer"
              >
                <option value="ALL TIERS">ALL TIERS</option>
                <option value="KEY">KEY</option>
                <option value="STRATEGIC">STRATEGIC</option>
                <option value="NORMAL">NORMAL</option>
              </select>
              <ChevronDown className="w-4 h-4 absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" aria-hidden="true" />
            </div>
          </div>

          <div className="text-sm text-muted-foreground" aria-live="polite">
            Showing {filteredAccounts.length} of {accounts.length}
          </div>
        </motion.div>

        {/* --- SECTION: Render - Accounts Table --- */}
        {/* Accounts table */}
        <motion.div
          initial={isFirstVisit ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ delay: isFirstVisit ? 0.15 : 0, duration: 0.4 }}
          className="bg-card border border-border rounded-lg overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm" aria-label="Accounts Directory">
              <thead>
                <tr className="border-b border-border bg-secondary/10">
                  <th
                    scope="col"
                    aria-sort={sortBy === 'name' ? 'ascending' : 'none'}
                    className="px-4 py-3 text-left font-semibold text-foreground"
                  >
                    <button
                      type="button"
                      onClick={() => setSortBy('name')}
                      aria-label="Sort by account name"
                      className="flex items-center gap-1.5 hover:text-primary transition-colors font-semibold"
                    >
                      <span>Account</span>
                      {sortBy === 'name' && <ChevronDown className="w-3.5 h-3.5 text-primary" aria-hidden="true" />}
                    </button>
                  </th>
                  <th scope="col" className="px-4 py-3 text-left font-semibold text-foreground">Industry</th>
                  <th scope="col" className="px-4 py-3 text-left font-semibold text-foreground">Territory</th>
                  <th scope="col" className="px-4 py-3 text-left font-semibold text-foreground">Tier</th>
                  <th
                    scope="col"
                    aria-sort={sortBy === 'health' ? 'descending' : 'none'}
                    className="px-4 py-3 text-left font-semibold text-foreground"
                  >
                    <button
                      type="button"
                      onClick={() => setSortBy('health')}
                      aria-label="Sort by health score"
                      className="flex items-center gap-1.5 hover:text-primary transition-colors font-semibold"
                    >
                      <span>Health</span>
                      {sortBy === 'health' && <ChevronDown className="w-3.5 h-3.5 text-primary" aria-hidden="true" />}
                    </button>
                  </th>
                  <th
                    scope="col"
                    aria-sort={sortBy === 'pipeline' ? 'descending' : 'none'}
                    className="px-4 py-3 text-left font-semibold text-foreground"
                  >
                    <button
                      type="button"
                      onClick={() => setSortBy('pipeline')}
                      aria-label="Sort by pipeline value"
                      className="flex items-center gap-1.5 hover:text-primary transition-colors font-semibold"
                    >
                      <span>Pipeline</span>
                      {sortBy === 'pipeline' && <ChevronDown className="w-3.5 h-3.5 text-primary" aria-hidden="true" />}
                    </button>
                  </th>
                  <th scope="col" className="px-4 py-3 text-left font-semibold text-foreground">Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <>
                    {[...Array(5)].map((_, i) => (
                      <tr key={`skeleton-${i}`} className="border-b border-border">
                        <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-6 w-20 rounded-sm" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                        <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                      </tr>
                    ))}
                  </>
                ) : filteredAccounts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">No accounts found.</td>
                  </tr>
                ) : (
                  filteredAccounts.map((account, index) => (
                    <motion.tr
                      key={account.Account_ID || index}
                      initial={isFirstVisit ? { opacity: 0 } : false}
                      animate={{ opacity: 1 }}
                      transition={{ delay: isFirstVisit ? 0.15 + index * 0.02 : 0 }}
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
  )
}
