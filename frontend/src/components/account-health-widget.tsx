'use client'

// AccountHealthWidget: dashboard card ranking accounts by computed health score
// (revenue, relationship depth, engagement, deal progression, support) so the
// weakest accounts surface first. Clicking a row opens an AI account plan.
// Major sections:
// - Health band helpers
// - Render: header, portfolio band summary, lowest-health account rows

import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { HeartPulse, ArrowRight } from 'lucide-react'
import { useData } from '@/context/DataContext'
import { accountPlanPrompt } from '@/components/risk-detection-panel'

const ROWS = 6

const band = (score: number) =>
  score < 30
    ? { label: 'Critical', text: 'text-destructive', bar: 'bg-destructive' }
    : score < 50
      ? { label: 'At risk', text: 'text-chart-3', bar: 'bg-chart-3' }
      : { label: 'Healthy', text: 'text-emerald-400', bar: 'bg-emerald-500' }

const formatCurrency = (val: number): string => {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

export function AccountHealthWidget() {
  const { accounts, loading } = useData()
  const router = useRouter()

  const ranked = [...accounts].sort((a, b) => (a.health_score ?? 0) - (b.health_score ?? 0))
  const counts = {
    critical: accounts.filter(a => (a.health_score ?? 0) < 30).length,
    atRisk: accounts.filter(a => (a.health_score ?? 0) >= 30 && (a.health_score ?? 0) < 50).length,
    healthy: accounts.filter(a => (a.health_score ?? 0) >= 50).length,
  }

  // --- SECTION: Render ---
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-card border border-border rounded-lg p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-base font-semibold text-foreground">Account Health</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Lowest-scoring accounts first · scored from revenue, contacts, engagement, deals and support
          </p>
        </div>
        <HeartPulse className="w-4 h-4 text-accent" />
      </div>

      {/* Portfolio band summary */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: 'Critical (<30)', value: counts.critical, cls: 'text-destructive' },
          { label: 'At risk (30–49)', value: counts.atRisk, cls: 'text-chart-3' },
          { label: 'Healthy (50+)', value: counts.healthy, cls: 'text-emerald-400' },
        ].map(m => (
          <div key={m.label} className="bg-secondary/30 border border-border p-3 rounded-md">
            <p className="text-xs text-muted-foreground">{m.label}</p>
            <p className={`text-xl font-semibold mt-1 ${m.cls}`}>{loading ? '–' : m.value}</p>
          </div>
        ))}
      </div>

      {/* Lowest-health accounts */}
      <div className="divide-y divide-border">
        {loading && [0, 1, 2, 3].map(i => <div key={i} className="h-11 my-1 rounded bg-secondary/30 animate-pulse" />)}
        {!loading && ranked.slice(0, ROWS).map(acc => {
          const score = Math.round(acc.health_score ?? 0)
          const b = band(score)
          return (
            <button
              key={acc.Account_ID}
              type="button"
              onClick={() => router.push(`/intelligence?q=${encodeURIComponent(accountPlanPrompt(acc.Account_Name))}`)}
              className="group w-full flex items-center gap-4 py-2.5 text-left hover:bg-secondary/30 rounded-sm px-1 transition-colors"
              title={`Build an AI account plan for ${acc.Account_Name}`}
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{acc.Account_Name}</p>
                <p className="text-xs text-muted-foreground">
                  {acc.Account_Tier} · {acc.Industry} · {formatCurrency(acc.total_pipeline_value || 0)} open pipeline
                </p>
              </div>
              <div className="w-28 hidden sm:block">
                <div className="h-1.5 rounded-full bg-secondary">
                  <div className={`h-1.5 rounded-full ${b.bar}`} style={{ width: `${Math.max(score, 3)}%` }} />
                </div>
              </div>
              <div className="w-20 text-right">
                <p className={`text-sm font-semibold ${b.text}`}>{score}</p>
                <p className="text-[11px] text-muted-foreground">{b.label}</p>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )
        })}
      </div>
    </motion.div>
  )
}
