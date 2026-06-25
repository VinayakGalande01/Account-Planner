'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { AccountHealthWidget } from '@/components/account-health-widget'
import { EngagementMomentumChart } from '@/components/engagement-momentum-chart'
import { RiskDetectionPanel } from '@/components/risk-detection-panel'
import { AICopilotPanel } from '@/components/ai-copilot-panel'
import { Sparkles } from 'lucide-react'

export default function Dashboard() {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false)

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col md:ml-0">
        {/* Header */}
        <Header />

        {/* Content area */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 md:p-8">
            {/* Page title */}
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-6"
            >
              <h1 className="text-3xl font-semibold text-foreground">
                Dashboard
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Real-time account intelligence and insights
              </p>
            </motion.div>

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

            {/* Quick stats section */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6"
            >
              {[
                { label: 'Active Accounts', value: '24' },
                { label: 'Total Pipeline', value: '$8.2M' },
                { label: 'Avg Health Score', value: '72/100' },
                { label: 'At-Risk Deals', value: '3' },
              ].map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.24 + index * 0.03 }}
                  className="bg-secondary/20 border border-border rounded-md p-3 text-center hover:bg-secondary/30 transition-colors duration-200"
                >
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold text-foreground mt-1.5">
                    {stat.value}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </main>
      </div>

      {/* AI Copilot button */}
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

      {/* AI Copilot Panel */}
      <AICopilotPanel isOpen={isCopilotOpen} onClose={() => setIsCopilotOpen(false)} />
    </div>
  )
}
