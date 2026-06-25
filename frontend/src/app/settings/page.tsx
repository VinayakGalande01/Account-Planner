'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import { Sidebar } from '@/components/sidebar'
import { Header } from '@/components/header'
import { Settings, Lock, Cpu } from 'lucide-react'

export default function SettingsPage() {
  const [modelConfig, setModelConfig] = useState({
    aiServer: '8000',
    claudeIntegration: 'LOCKED',
  })

  const [securityConfig, setSecurityConfig] = useState({
    dataEncryption: 'AES-256',
    accessLevel: 'ADMIN PRIORITY',
  })

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
              className="mb-8"
            >
              <div className="flex items-center gap-2">
                <Settings className="w-6 h-6 text-primary" />
                <h1 className="text-3xl font-semibold text-foreground">System Settings</h1>
              </div>
            </motion.div>

            {/* Settings grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Model Configuration */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.4 }}
                className="bg-card border border-border rounded-lg p-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <Cpu className="w-5 h-5 text-primary" />
                  <h2 className="text-base font-semibold text-foreground">Model Configuration</h2>
                </div>

                <div className="space-y-4">
                  {/* AI Server Endpoint */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      AI Server Endpoint
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="text"
                        defaultValue="localhost"
                        disabled
                        className="flex-1 bg-secondary border border-border rounded-md px-3 py-1.5 text-sm text-muted-foreground disabled:opacity-50"
                      />
                      <span className="px-3 py-1.5 bg-accent/20 text-accent text-sm font-medium rounded-md">
                        ACTIVE: {modelConfig.aiServer}
                      </span>
                    </div>
                  </div>

                  {/* Claude Integration */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Claude-3 Integration
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="text"
                        defaultValue="Claude-3 Integration"
                        disabled
                        className="flex-1 bg-secondary border border-border rounded-md px-3 py-1.5 text-sm text-muted-foreground disabled:opacity-50"
                      />
                      <span className="px-3 py-1.5 bg-muted/20 text-muted-foreground text-sm font-medium rounded-md">
                        {modelConfig.claudeIntegration}
                      </span>
                    </div>
                  </div>

                  {/* Model Status */}
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-2">System Status</p>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                      <span className="text-sm text-foreground">All systems operational</span>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Security Settings */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.4 }}
                className="bg-card border border-border rounded-lg p-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <Lock className="w-5 h-5 text-primary" />
                  <h2 className="text-base font-semibold text-foreground">Security Settings</h2>
                </div>

                <div className="space-y-4">
                  {/* Data Encryption */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Data Encryption
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="text"
                        defaultValue="AES-256"
                        disabled
                        className="flex-1 bg-secondary border border-border rounded-md px-3 py-1.5 text-sm text-muted-foreground disabled:opacity-50"
                      />
                      <span className="px-3 py-1.5 bg-accent/20 text-accent text-sm font-medium rounded-md">
                        {securityConfig.dataEncryption}
                      </span>
                    </div>
                  </div>

                  {/* Access Level */}
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Access Level
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="text"
                        defaultValue="Admin"
                        disabled
                        className="flex-1 bg-secondary border border-border rounded-md px-3 py-1.5 text-sm text-muted-foreground disabled:opacity-50"
                      />
                      <span className="px-3 py-1.5 bg-chart-3/20 text-chart-3 text-sm font-medium rounded-md">
                        {securityConfig.accessLevel}
                      </span>
                    </div>
                  </div>

                  {/* Security Status */}
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-2">Security Status</p>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                      <span className="text-sm text-foreground">All security protocols active</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Advanced Settings */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.4 }}
              className="mt-6 bg-card border border-border rounded-lg p-6"
            >
              <h2 className="text-base font-semibold text-foreground mb-4">Advanced Configuration</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* API Settings */}
                <div>
                  <p className="text-sm text-muted-foreground mb-3">API Endpoints</p>
                  <div className="space-y-2">
                    {[
                      { name: 'REST API', status: 'Active' },
                      { name: 'WebSocket', status: 'Active' },
                      { name: 'GraphQL', status: 'Configured' },
                    ].map((endpoint) => (
                      <div key={endpoint.name} className="flex items-center justify-between px-3 py-2 bg-secondary/20 border border-border rounded-md">
                        <span className="text-sm text-foreground">{endpoint.name}</span>
                        <span className="text-xs px-2 py-0.5 bg-accent/15 text-accent rounded-sm">
                          {endpoint.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Database Settings */}
                <div>
                  <p className="text-sm text-muted-foreground mb-3">Database Configuration</p>
                  <div className="space-y-2">
                    {[
                      { name: 'Primary DB', status: 'Connected' },
                      { name: 'Cache Layer', status: 'Active' },
                      { name: 'Backups', status: 'Scheduled' },
                    ].map((db) => (
                      <div key={db.name} className="flex items-center justify-between px-3 py-2 bg-secondary/20 border border-border rounded-md">
                        <span className="text-sm text-foreground">{db.name}</span>
                        <span className="text-xs px-2 py-0.5 bg-accent/15 text-accent rounded-sm">
                          {db.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>

            {/* System Status */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4 }}
              className="mt-6 bg-card border border-border rounded-lg p-6"
            >
              <h2 className="text-base font-semibold text-foreground mb-4">System Online</h2>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-accent rounded-full animate-pulse" />
                <div>
                  <p className="text-sm text-foreground">Backend: 8002 | LLM: 8000</p>
                  <p className="text-xs text-muted-foreground mt-1">All services operational</p>
                </div>
              </div>
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  )
}
