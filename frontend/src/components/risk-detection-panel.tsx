'use client'

import { motion } from 'framer-motion'
import { AlertTriangle, TrendingDown, Clock, Users } from 'lucide-react'

const risks = [
  {
    id: 1,
    title: 'Single-threaded Deal Detected',
    account: 'Acme Corp',
    severity: 'critical',
    description: 'Only one stakeholder engaged in current opportunity',
    icon: Users,
  },
  {
    id: 2,
    title: 'Stalled Opportunity',
    account: 'Acme Corp',
    severity: 'high',
    description: 'No activity for 45+ days on $500K deal',
    icon: Clock,
  },
  {
    id: 3,
    title: 'Revenue at Risk',
    account: 'Acme Corp',
    severity: 'high',
    description: '$2.1M renewal due in 60 days, no champion identified',
    icon: TrendingDown,
  },
  {
    id: 4,
    title: 'Competitor Activity Detected',
    account: 'Acme Corp',
    severity: 'medium',
    description: 'LinkedIn posts indicate they&apos;re evaluating alternatives',
    icon: AlertTriangle,
  },
]

const severityConfig = {
  critical: {
    border: 'border-l-2 border-l-destructive',
    badge: 'bg-destructive/15 text-destructive',
    dot: 'bg-destructive',
  },
  high: {
    border: 'border-l-2 border-l-chart-3',
    badge: 'bg-chart-3/15 text-chart-3',
    dot: 'bg-chart-3',
  },
  medium: {
    border: 'border-l-2 border-l-primary',
    badge: 'bg-primary/15 text-primary',
    dot: 'bg-primary',
  },
}

export function RiskDetectionPanel() {
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
            AI-detected alerts
          </p>
        </div>
        <div className="flex items-center justify-center w-8 h-8 rounded-md bg-destructive/10">
          <AlertTriangle className="w-4 h-4 text-destructive" />
        </div>
      </div>

      {/* Risk list */}
      <div className="space-y-2">
        {risks.map((risk, index) => {
          const config = severityConfig[risk.severity as keyof typeof severityConfig]
          const Icon = risk.icon

          return (
            <motion.div
              key={risk.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + index * 0.04 }}
              whileHover={{ x: 2 }}
              className={`p-3 bg-secondary/30 border border-border ${config.border} rounded-md cursor-pointer transition-colors hover:bg-secondary/50`}
            >
              <div className="flex items-start gap-2.5">
                <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${config.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {risk.title}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {risk.description}
                      </p>
                    </div>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-sm whitespace-nowrap ${config.badge}`}
                    >
                      {risk.severity.charAt(0).toUpperCase() + risk.severity.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Action button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className="w-full mt-4 py-2 px-4 bg-primary text-primary-foreground rounded-md font-medium text-sm hover:bg-primary/90 transition-colors"
      >
        Review All Risks
      </motion.button>
    </motion.div>
  )
}
