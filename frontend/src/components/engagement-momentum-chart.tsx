'use client'

// EngagementMomentumChart: dashboard card charting email/call/meeting
// activity trend over the last 90 days via a stacked area chart.
// Major sections:
// - Static series data
// - Render: header + metrics summary, area chart, legend

import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Activity } from 'lucide-react'

const data = [
  { date: 'Mar 1', emails: 12, calls: 8, meetings: 2 },
  { date: 'Mar 8', emails: 19, calls: 10, meetings: 4 },
  { date: 'Mar 15', emails: 15, calls: 14, meetings: 6 },
  { date: 'Mar 22', emails: 25, calls: 18, meetings: 8 },
  { date: 'Mar 29', emails: 22, calls: 16, meetings: 7 },
  { date: 'Apr 5', emails: 28, calls: 20, meetings: 9 },
  { date: 'Apr 12', emails: 32, calls: 24, meetings: 11 },
  { date: 'Apr 19', emails: 35, calls: 28, meetings: 13 },
  { date: 'Apr 26', emails: 38, calls: 30, meetings: 15 },
]

export function EngagementMomentumChart() {
  // --- SECTION: Render ---
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="bg-card border border-border rounded-lg p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-base font-semibold text-foreground">
            Engagement Momentum
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Last 90 days activity
          </p>
        </div>
        <Activity className="w-4 h-4 text-primary" />
      </div>

      {/* Activity metrics */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {[
          { label: 'Emails', value: '226', trend: '+18%' },
          { label: 'Calls', value: '168', trend: '+22%' },
          { label: 'Meetings', value: '84', trend: '+15%' },
        ].map((metric, index) => (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.15 + index * 0.04 }}
            className="bg-secondary/30 border border-border p-2.5 rounded-md text-center"
          >
            <p className="text-xs text-muted-foreground">{metric.label}</p>
            <p className="text-base font-semibold text-foreground mt-0.5">
              {metric.value}
            </p>
            <p className="text-xs text-accent mt-0.5">{metric.trend}</p>
          </motion.div>
        ))}
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorEmails" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3366cc" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3366cc" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22a366" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#22a366" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorMeetings" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#dab538" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#dab538" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#ffffff0a"
              vertical={false}
            />
            <XAxis dataKey="date" stroke="#8a8a96" style={{ fontSize: '11px' }} />
            <YAxis stroke="#8a8a96" style={{ fontSize: '11px' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a20',
                border: '1px solid #ffffff10',
                borderRadius: '6px',
              }}
              labelStyle={{ color: '#e8e8eb' }}
            />
            <Area
              type="monotone"
              dataKey="emails"
              stroke="#3366cc"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorEmails)"
            />
            <Area
              type="monotone"
              dataKey="calls"
              stroke="#22a366"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorCalls)"
            />
            <Area
              type="monotone"
              dataKey="meetings"
              stroke="#dab538"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorMeetings)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex gap-5 mt-3 text-xs">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-chart-1" />
          <span className="text-muted-foreground">Emails</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-chart-2" />
          <span className="text-muted-foreground">Calls</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-chart-3" />
          <span className="text-muted-foreground">Meetings</span>
        </div>
      </div>
    </motion.div>
  )
}
