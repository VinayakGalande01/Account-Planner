'use client'

// AccountHealthWidget: dashboard card showing a single account's health
// score, key metrics grid, and an engagement-mix pie chart.
// Major sections:
// - Static chart data
// - Render: header, metrics grid, health gauge + pie chart, legend

import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import { TrendingUp } from 'lucide-react'

const data = [
  { name: 'Engaged', value: 75, color: '#22a366' },
  { name: 'At Risk', value: 15, color: '#dab538' },
  { name: 'Inactive', value: 10, color: '#4a4a54' },
]

export function AccountHealthWidget() {
  const healthScore = 78

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
          <h3 className="text-base font-semibold text-foreground">
            Account Health
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Acme Corp
          </p>
        </div>
        <TrendingUp className="w-4 h-4 text-accent" />
      </div>

      {/* Health metrics */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        {[
          { label: 'Revenue', value: '$2.4M', trend: '+12%' },
          { label: 'Engagement', value: '94%', trend: '+8%' },
          { label: 'Deal Progression', value: '78%', trend: '+5%' },
          { label: 'Last Contact', value: '3 days', trend: 'ago' },
        ].map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.04 }}
            className="bg-secondary/30 border border-border p-3 rounded-md"
          >
            <p className="text-xs text-muted-foreground">{metric.label}</p>
            <p className="text-sm font-medium text-foreground mt-1">
              {metric.value}
            </p>
            <p className="text-xs text-accent mt-0.5">{metric.trend}</p>
          </motion.div>
        ))}
      </div>

      {/* Health gauge visualization */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-5xl font-semibold text-foreground">
            {healthScore}
            <span className="text-sm text-muted-foreground ml-1">/100</span>
          </div>
          <p className="text-xs text-accent mt-2 font-medium">Healthy</p>
        </div>

        {/* Pie chart */}
        <div className="w-32 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={42}
                outerRadius={64}
                paddingAngle={1}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-3 mt-5 text-xs">
        {data.map((item) => (
          <div key={item.name} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-muted-foreground">
              {item.name} ({item.value}%)
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
