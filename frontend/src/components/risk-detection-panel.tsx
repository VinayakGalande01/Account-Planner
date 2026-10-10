'use client'

// RiskDetectionPanel: dashboard card listing risks detected from live CRM data
// (/api/insights: critical cases, single-threaded deals, stalled accounts, low CSAT).
// Clicking a risk opens the AI assistant with an account plan request for that account.
// Major sections:
// - Data fetch + severity style config
// - Render: header, risk list, review-all action button

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { AlertTriangle, ArrowRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

interface Insight {
  id: string
  type: 'critical' | 'warning' | 'opportunity'
  title: string
  description: string
  targetAccount: string
}

const severityConfig = {
  critical: {
    border: 'border-l-2 border-l-destructive',
    badge: 'bg-destructive/15 text-destructive',
    dot: 'bg-destructive',
    label: 'Critical',
  },
  warning: {
    border: 'border-l-2 border-l-chart-3',
    badge: 'bg-chart-3/15 text-chart-3',
    dot: 'bg-chart-3',
    label: 'High',
  },
}

interface AccountRisk {
  account: string
  severity: 'critical' | 'warning'
  items: Insight[]
}

const MAX_ACCOUNTS = 4

// One card per account so a single account's alerts don't crowd out the rest
const groupByAccount = (insights: Insight[]): AccountRisk[] => {
  const groups = new Map<string, AccountRisk>()
  for (const i of insights) {
    const g = groups.get(i.targetAccount) ?? { account: i.targetAccount, severity: 'warning', items: [] }
    g.items.push(i)
    if (i.type === 'critical') g.severity = 'critical'
    groups.set(i.targetAccount, g)
  }
  return [...groups.values()].sort(
    (a, b) => (a.severity === b.severity ? b.items.length - a.items.length : a.severity === 'critical' ? -1 : 1)
  )
}

export const accountPlanPrompt = (account: string) => `Build an account plan for ${account}`

export function RiskDetectionPanel() {
  const { authFetch } = useAuth()
  const router = useRouter()
  const [risks, setRisks] = useState<AccountRisk[] | null>(null)

  useEffect(() => {
    let active = true
    authFetch('/api/insights')
      .then(res => (res.ok ? res.json() : { insights: [] }))
      .then(data => {
        if (!active) return
        const list: Insight[] = (data.insights || []).filter((i: Insight) => i.type !== 'opportunity')
        setRisks(groupByAccount(list))
      })
      .catch(() => active && setRisks([]))
    return () => { active = false }
  }, [authFetch])

  const openPlan = (account: string) =>
    router.push(`/intelligence?q=${encodeURIComponent(accountPlanPrompt(account))}`)

  // --- SECTION: Render ---
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="bg-card border border-border rounded-lg p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-base font-semibold text-foreground">Risk Detection</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {risks ? `${risks.length} accounts flagged from CRM data` : 'Scanning CRM data...'}
          </p>
        </div>
        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-destructive/10">
          <AlertTriangle className="w-4 h-4 text-destructive" />
        </div>
      </div>

      {/* Risk list */}
      <div className="space-y-2">
        {risks === null &&
          [0, 1, 2].map(i => <div key={i} className="h-16 rounded-md bg-secondary/30 animate-pulse" />)}
        {risks?.length === 0 && (
          <p className="text-sm text-muted-foreground">No open risks detected.</p>
        )}
        {risks?.slice(0, MAX_ACCOUNTS).map((risk, index) => {
          const config = severityConfig[risk.severity]
          return (
            <motion.button
              key={risk.account}
              type="button"
              onClick={() => openPlan(risk.account)}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + index * 0.04 }}
              whileHover={{ x: 2 }}
              title={`Build an AI account plan for ${risk.account}`}
              className={`group w-full text-left p-3 bg-secondary/30 border border-border ${config.border} rounded-md cursor-pointer transition-colors hover:bg-secondary/50`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{risk.account}</p>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-sm whitespace-nowrap ${config.badge}`}>
                  {config.label}
                </span>
              </div>
              <ul className="mt-1.5 space-y-1">
                {risk.items.slice(0, 3).map(item => (
                  <li key={item.id} className="flex gap-2 text-xs text-muted-foreground">
                    <span className={`w-1 h-1 rounded-full mt-1.5 flex-shrink-0 ${config.dot}`} />
                    <span>{item.title}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 flex items-center gap-1 text-xs font-medium text-primary opacity-80 group-hover:opacity-100">
                Generate AI account plan <ArrowRight className="w-3 h-3" />
              </p>
            </motion.button>
          )
        })}
      </div>

      {/* Action button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => router.push(`/intelligence?q=${encodeURIComponent('Show me accounts at high risk')}`)}
        className="w-full mt-4 py-2 px-4 bg-primary text-primary-foreground rounded-md font-medium text-sm hover:bg-primary/90 transition-colors"
      >
        Ask APEX About All Risks
      </motion.button>
    </motion.div>
  )
}
