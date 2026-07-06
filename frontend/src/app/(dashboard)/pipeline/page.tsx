'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { AICopilotPanel } from '@/components/ai-copilot-panel'
import { Sparkles, TrendingUp } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

export default function PipelinePage() {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false)
  
  const { authFetch } = useAuth()
  const [pipelineData, setPipelineData] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)

  // What-If Simulator States
  const [winRateBoost, setWinRateBoost] = useState(0) // in percent
  const [dealSizeExpansion, setDealSizeExpansion] = useState(1.0) // multiplier
  const [cycleAcceleration, setCycleAcceleration] = useState(0) // percent

  useEffect(() => {
    authFetch('/api/pipeline/summary')
      .then(res => res.json())
      .then(data => {
        setPipelineData(data.stage_summary || {})
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const formatCurrency = (val: number): string => {
    if (!val && val !== 0) return '—'
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(2)}M`
    if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
    return `$${val.toFixed(0)}`
  }

  const totalPipeline = Object.entries(pipelineData)
    .filter(([k]) => k !== 'Closed Won' && k !== 'Closed Lost')
    .reduce((sum, [, v]) => sum + v, 0)
    
  const closedWon = pipelineData['Closed Won'] || 0

  const simTotalPipeline = totalPipeline * dealSizeExpansion * (1 - cycleAcceleration * 0.005)
  const simClosedWon = closedWon + (totalPipeline * (0.15 + winRateBoost / 100) * dealSizeExpansion * (1 + cycleAcceleration * 0.012))

  const STAGES = [
    'Prospecting', 'Qualification', 'Needs Analysis', 'Value Proposition',
    'Id. Decision Makers', 'Perception Analysis', 'Proposal/Price Quote',
    'Negotiation/Review', 'Closed Won', 'Closed Lost'
  ]

  const stagesData = STAGES.filter(s => pipelineData[s] !== undefined).map(stage => ({
    stage,
    current: (pipelineData[stage] || 0) / 1000000,
    simulated: ((pipelineData[stage] || 0) * (stage === 'Closed Won' ? 1.0 : dealSizeExpansion)) / 1000000
  }))

  const baseForecasted = [2.1, 2.4, 2.8, 3.1, 3.6, 4.0, 4.2]
  const actual = [1.8, 2.2, 2.5, 2.9, 3.2, 3.4, 3.9]
  
  const simulatedForecast = baseForecasted.map(v => 
    v * dealSizeExpansion * (1 + (winRateBoost * 0.012) + (cycleAcceleration * 0.008))
  )

  const salesSpeedData = [
    { month: 'Jan', forecast: baseForecasted[0], simulation: simulatedForecast[0], actual: actual[0] },
    { month: 'Feb', forecast: baseForecasted[1], simulation: simulatedForecast[1], actual: actual[1] },
    { month: 'Mar', forecast: baseForecasted[2], simulation: simulatedForecast[2], actual: actual[2] },
    { month: 'Apr', forecast: baseForecasted[3], simulation: simulatedForecast[3], actual: actual[3] },
    { month: 'May', forecast: baseForecasted[4], simulation: simulatedForecast[4], actual: actual[4] },
    { month: 'Jun', forecast: baseForecasted[5], simulation: simulatedForecast[5], actual: actual[5] },
  ]


  return (
    <div className="flex h-screen bg-background">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <Header />

        <main className="flex-1 overflow-y-auto">
          <div className="p-6 md:p-8">
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-6"
            >
              <div className="flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-primary" />
                <h1 className="text-3xl font-semibold text-foreground">Pipeline</h1>
              </div>
              <p className="text-sm text-muted-foreground mt-1">Sales Speed - Actual vs Simulation</p>
            </motion.div>

            {loading ? (
              <div className="text-center py-10 text-muted-foreground">Loading pipeline data...</div>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                  {[
                    { label: 'Open Pipeline', value: formatCurrency(totalPipeline) },
                    { label: 'Closed Won', value: formatCurrency(closedWon) },
                    { label: 'Simulated Pipeline', value: formatCurrency(simTotalPipeline) },
                    { label: 'Simulated Won', value: formatCurrency(simClosedWon) },
                  ].map((metric, index) => (
                    <motion.div
                      key={metric.label}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.1 + index * 0.03 }}
                      className="bg-secondary/20 border border-border rounded-md p-3 text-center"
                    >
                      <p className="text-xs text-muted-foreground">{metric.label}</p>
                      <p className="text-lg font-semibold text-foreground mt-1.5">{metric.value}</p>
                    </motion.div>
                  ))}
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15, duration: 0.4 }}
                  className="bg-card border border-border rounded-lg p-5 mb-6"
                >
                  <h3 className="text-base font-semibold text-foreground mb-4">
                    Sales Speed: Actual vs Simulation
                  </h3>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={salesSpeedData}>
                        <defs>
                          <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3366cc" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#3366cc" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                        <XAxis dataKey="month" stroke="#8a8a96" style={{ fontSize: '11px' }} />
                        <YAxis stroke="#8a8a96" style={{ fontSize: '11px' }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1a1a20',
                            border: '1px solid #ffffff10',
                            borderRadius: '6px',
                          }}
                          labelStyle={{ color: '#e8e8eb' }}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Line
                          type="monotone"
                          dataKey="forecast"
                          stroke="#3366cc"
                          strokeWidth={2}
                          strokeDasharray="5 5"
                          name="Forecast (M)"
                        />
                        <Line
                          type="monotone"
                          dataKey="simulation"
                          stroke="#22a366"
                          strokeWidth={2}
                          name="Simulation (M)"
                        />
                        <Line
                          type="monotone"
                          dataKey="actual"
                          stroke="#e8e8eb"
                          strokeWidth={2}
                          name="Actual (M)"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.4 }}
                  className="bg-card border border-border rounded-lg p-5 mb-6"
                >
                  <h3 className="text-base font-semibold text-foreground mb-4">
                    Sales Stages (Current vs Simulated)
                  </h3>
                  <div className="h-96">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stagesData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                        <XAxis dataKey="stage" stroke="#8a8a96" style={{ fontSize: '10px' }} angle={-45} textAnchor="end" height={100} />
                        <YAxis stroke="#8a8a96" style={{ fontSize: '11px' }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#1a1a20',
                            border: '1px solid #ffffff10',
                            borderRadius: '6px',
                          }}
                          labelStyle={{ color: '#e8e8eb' }}
                          formatter={(value) => [`$${Number(value).toFixed(2)}M`]}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px' }} />
                        <Bar dataKey="current" fill="#3366cc" name="Current (M)" />
                        <Bar dataKey="simulated" fill="#22a366" name="Simulated (M)" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25, duration: 0.4 }}
                  className="bg-card border border-border rounded-lg p-5"
                >
                  <h3 className="text-base font-semibold text-foreground mb-4">Sales Simulation Levers</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-secondary/20 border border-border rounded-md p-4">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-xs text-muted-foreground">Win Rate Boost</p>
                        <span className="text-sm font-semibold">{winRateBoost >= 0 ? '+' : ''}{winRateBoost}%</span>
                      </div>
                      <input type="range" min="-15" max="25" value={winRateBoost} onChange={(e) => setWinRateBoost(parseInt(e.target.value))} className="w-full accent-primary" />
                    </div>
                    <div className="bg-secondary/20 border border-border rounded-md p-4">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-xs text-muted-foreground">Deal Size Multiplier</p>
                        <span className="text-sm font-semibold">{dealSizeExpansion.toFixed(2)}x</span>
                      </div>
                      <input type="range" min="50" max="175" value={dealSizeExpansion * 100} onChange={(e) => setDealSizeExpansion(parseInt(e.target.value)/100)} className="w-full accent-primary" />
                    </div>
                    <div className="bg-secondary/20 border border-border rounded-md p-4">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-xs text-muted-foreground">Sales Cycle Speedup</p>
                        <span className="text-sm font-semibold">+{cycleAcceleration}%</span>
                      </div>
                      <input type="range" min="0" max="40" value={cycleAcceleration} onChange={(e) => setCycleAcceleration(parseInt(e.target.value))} className="w-full accent-primary" />
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </div>
        </main>
      </div>

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
