'use client'

/**
 * SYSTEM SETTINGS PAGE (settings/page.tsx)
 * Renders system configurations including active local/cloud LLM model servers,
 * security encryption variables, and local caching parameters.
 */

// --- SECTION 1: Dependencies & State Hooks ---
// Imports motion UI frameworks, configuration state variables, and page layout headers.
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useAnimation } from '@/context/AnimationContext'
import { Settings, Lock, Cpu } from 'lucide-react'

import { PageHeader } from '@/components/common/PageHeader'

// --- SECTION 2: Settings Component & Render Layout ---
// Manages LLM server provider selections and displays security settings tab grids.
export default function SettingsPage() {
  const { isFirstVisit } = useAnimation()
  
  const [modelConfig, setModelConfig] = useState({
    aiServer: '8000',
    claudeIntegration: 'LOCKED',
  })

  const [llmProvider, setLlmProvider] = useState('local')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setLlmProvider(localStorage.getItem('llm_provider') || 'local')
    }
  }, [])

  const [securityConfig, setSecurityConfig] = useState({
    dataEncryption: 'AES-256',
    accessLevel: 'ADMIN PRIORITY',
  })

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="p-6 md:p-8">
        <PageHeader
          title="System Settings"
          subtitle="Model server, provider config, and system security"
          icon={<Settings className="w-6 h-6" />}
        />

            {/* Settings grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Model Configuration */}
            <motion.div
              initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: isFirstVisit ? 0.1 : 0, duration: 0.4 }}
              className="bg-card border border-border rounded-lg p-6"
            >
                <div className="flex items-center gap-3 mb-6">
                  <Cpu className="w-5 h-5 text-primary" />
                  <h2 className="text-base font-semibold text-foreground">Model Configuration</h2>
                </div>

                <div className="space-y-4">
                  {/* AI Server Endpoint */}
                  <div className="flex items-center justify-between p-3 bg-secondary/30 border border-border rounded-md">
                    <div>
                      <p className="text-xs font-medium text-foreground">AI Server Endpoint</p>
                      <p className="text-xs text-muted-foreground mt-0.5">localhost</p>
                    </div>
                    <span className="px-2.5 py-1 bg-accent/20 text-accent text-xs font-semibold rounded-md">
                      ACTIVE: {modelConfig.aiServer}
                    </span>
                  </div>

                  {/* Reasoning Model Provider */}
                  <div>
                    <label htmlFor="llm-provider-select" className="block text-xs font-medium text-foreground mb-2">
                      AI Reasoning Provider
                    </label>
                    <select
                      id="llm-provider-select"
                      value={llmProvider}
                      onChange={(e) => {
                        const val = e.target.value
                        setLlmProvider(val)
                        localStorage.setItem('llm_provider', val)
                      }}
                      className="w-full bg-secondary border border-border rounded-md px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="local">Local Model (Ollama on Port 8000)</option>
                      <option value="gemini">Cloud Model (Google Gemini API)</option>
                    </select>
                  </div>

                  {/* Claude Integration */}
                  <div className="flex items-center justify-between p-3 bg-secondary/30 border border-border rounded-md">
                    <div>
                      <p className="text-xs font-medium text-foreground">Claude-3 Integration</p>
                      <p className="text-xs text-muted-foreground mt-0.5">Anthropic API Protocol</p>
                    </div>
                    <span className="px-2.5 py-1 bg-muted/30 text-muted-foreground text-xs font-semibold rounded-md">
                      {modelConfig.claudeIntegration}
                    </span>
                  </div>

                  {/* Model Status */}
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-2">System Status</p>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                      <span className="text-xs text-foreground">All systems operational</span>
                    </div>
                  </div>
                </div>
              </motion.div>

            {/* Security Settings */}
            <motion.div
              initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: isFirstVisit ? 0.15 : 0, duration: 0.4 }}
              className="bg-card border border-border rounded-lg p-6"
            >
                <div className="flex items-center gap-3 mb-6">
                  <Lock className="w-5 h-5 text-primary" />
                  <h2 className="text-base font-semibold text-foreground">Security Settings</h2>
                </div>

                <div className="space-y-4">
                  {/* Data Encryption */}
                  <div className="flex items-center justify-between p-3 bg-secondary/30 border border-border rounded-md">
                    <div>
                      <p className="text-xs font-medium text-foreground">Data Encryption</p>
                      <p className="text-xs text-muted-foreground mt-0.5">End-to-end payload encryption</p>
                    </div>
                    <span className="px-2.5 py-1 bg-accent/20 text-accent text-xs font-semibold rounded-md">
                      {securityConfig.dataEncryption}
                    </span>
                  </div>

                  {/* Access Level */}
                  <div className="flex items-center justify-between p-3 bg-secondary/30 border border-border rounded-md">
                    <div>
                      <p className="text-xs font-medium text-foreground">Access Level</p>
                      <p className="text-xs text-muted-foreground mt-0.5">Role-Based Access Control (RBAC)</p>
                    </div>
                    <span className="px-2.5 py-1 bg-chart-3/20 text-chart-3 text-xs font-semibold rounded-md">
                      {securityConfig.accessLevel}
                    </span>
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
            initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: isFirstVisit ? 0.2 : 0, duration: 0.4 }}
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

          {/* Golden Dataset & Eval Section */}
          <motion.div
            initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: isFirstVisit ? 0.22 : 0, duration: 0.4 }}
            className="mt-6 bg-card border border-border rounded-lg p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-foreground">Golden Dataset & QA Benchmarks</h2>
                <p className="text-xs text-muted-foreground mt-1">Internal prompt evaluation testcases and intent classifier benchmarks</p>
              </div>
              <a
                href="/datasets"
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-md hover:bg-primary/90 transition-colors"
              >
                Manage Testcases
              </a>
            </div>
            <div className="p-3 bg-secondary/30 border border-border rounded-md text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">Admin Note:</span> This evaluation dataset is used by engineering to benchmark AI response accuracy and classifier accuracy. It is excluded from daily salesperson navigation.
            </div>
          </motion.div>

          {/* System Status */}
          <motion.div
            initial={isFirstVisit ? { opacity: 0, y: 12 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: isFirstVisit ? 0.25 : 0, duration: 0.4 }}
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
  )
}
