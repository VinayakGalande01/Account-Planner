'use client'

/**
 * DASHBOARD VIEW SHELL (dashboard-shell.tsx)
 * Orchestrates main authenticated layout boundaries, combining collapsible sidebars,
 * top headers, nested children page views, and floating AI Copilot button toggles.
 */

// --- SECTION 1: Dependencies & Core Components ---
// Imports motion animation frameworks, sidebars, headers, and copilot panels.
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sidebar } from '@/components/Sidebar'
import { Header } from '@/components/header'
import { AICopilotPanel } from '@/components/ai-copilot-panel'
import { Sparkles } from 'lucide-react'

// --- SECTION 2: Dashboard Shell Layout ---
// Renders sidebar grid coordinates, main page sections, and floating action copilot elements.
export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false)

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div id="main-content" tabIndex={-1} className="flex-1 flex flex-col md:ml-0 overflow-hidden outline-none">
        <Header />
        {children}
      </div>

      <motion.button
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.3 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsCopilotOpen(true)}
        aria-label="Open AI Copilot panel"
        className="fixed bottom-6 right-6 md:bottom-8 md:right-8 w-12 h-12 bg-primary rounded-lg flex items-center justify-center shadow-md hover:shadow-lg hover:bg-primary/90 transition-all z-30"
      >
        <Sparkles className="w-5 h-5 text-primary-foreground" />
      </motion.button>

      <AICopilotPanel isOpen={isCopilotOpen} onClose={() => setIsCopilotOpen(false)} />
    </div>
  )
}
