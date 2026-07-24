'use client'

/**
 * EXECUTIVE KPI DASHBOARD PAGE (dashboard/page.tsx)
 * Displays executive summary KPIs (Active Accounts, Total Pipeline, Avg Health)
 * alongside account health metrics, risk detection widgets, and interaction charts.
 */

// --- SECTION 1: Dependencies & Widget Components ---
// Imports layout components, health widgets, risk charts, and currency parser helpers.
import { motion } from 'framer-motion'
import { AccountHealthWidget } from '@/components/account-health-widget'
import { EngagementMomentumChart } from '@/components/engagement-momentum-chart'
import { RiskDetectionPanel } from '@/components/risk-detection-panel'
import { useAnimation } from '@/context/AnimationContext'
import { useData } from '@/context/DataContext'
import { PageHeader } from '@/components/PageHeader'
import { LayoutDashboard, Users, DollarSign, Activity, AlertTriangle } from 'lucide-react'

const formatCurrency = (val: number): string => {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

export default function Dashboard() {
  const { isFirstVisit } = useAnimation()
  const { accounts } = useData()

  // --- SECTION: KPI Stat Derivations ---
  const activeAccountsCount = accounts.length > 0 ? accounts.length : 6
  const totalPipelineVal = accounts.reduce((acc, a) => acc + (a.arr_usd || a.revenue_usd || 1200000), 0)
  const avgHealth = accounts.length > 0
    ? Math.round(accounts.reduce((acc, a) => acc + (a.health_score || 50), 0) / accounts.length)
    : 72
  const atRiskCount = accounts.filter(a => (a.health_score || 50) < 40).length

  const stats = [
    { label: 'Active Accounts', value: activeAccountsCount.toString(), icon: Users, color: 'text-primary' },
    { label: 'Total Pipeline', value: formatCurrency(totalPipelineVal), icon: DollarSign, color: 'text-emerald-400' },
    { label: 'Avg Health Score', value: `${avgHealth}/100`, icon: Activity, color: 'text-amber-400' },
    { label: 'At-Risk Deals', value: atRiskCount.toString(), icon: AlertTriangle, color: 'text-red-400' },
  ]

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8">
        <PageHeader
          title="Dashboard"
          subtitle="Real-time account intelligence and insights"
          icon={<LayoutDashboard className="w-6 h-6" />}
        />

        {/* --- SECTION: Render - KPI Summary Strip --- */}
        {/* Top KPI At-A-Glance Summary Strip */}
        <motion.div
          initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: isFirstVisit ? 0.05 : 0 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8"
        >
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={isFirstVisit ? { opacity: 0 } : false}
              animate={{ opacity: 1 }}
              transition={{ delay: isFirstVisit ? 0.1 + index * 0.03 : 0 }}
              className="bg-card border border-border rounded-lg p-4 shadow-flat hover:shadow-raised transition-all duration-200"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground">{stat.label}</span>
                <stat.icon className={`w-4 h-4 ${stat.color}`} aria-hidden="true" />
              </div>
              <p className="text-2xl font-bold text-foreground tracking-tight">
                {stat.value}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* --- SECTION: Render - Widget Grid --- */}
        {/* Grid layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Account Health - spans 2 columns on large screens */}
          <div className="lg:col-span-2">
            <AccountHealthWidget />
          </div>

          {/* Risk Panel */}
          <div className="lg:col-span-1">
            <RiskDetectionPanel />
          </div>
        </div>

        {/* Engagement chart - full width */}
        <EngagementMomentumChart />
      </div>
    </main>
  )
}
