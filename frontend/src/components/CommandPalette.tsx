'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Briefcase, LayoutDashboard, TrendingUp, Brain, Settings, X, Command } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

const searchableAccounts = [
  { name: 'Acme Corp', tier: 'Tier 1', health: 85, href: '/accounts' },
  { name: 'Solace Health', tier: 'Tier 1', health: 18, href: '/accounts' },
  { name: 'Nexus Dynamics', tier: 'Tier 2', health: 74, href: '/accounts' },
  { name: 'Horizon Media', tier: 'Tier 2', health: 91, href: '/accounts' },
  { name: 'Cyberdyne Systems', tier: 'Tier 1', health: 42, href: '/accounts' },
  { name: 'Omni Consumer Products', tier: 'Tier 3', health: 68, href: '/accounts' },
]

const navigationItems = [
  { name: 'Dashboard Overview', icon: LayoutDashboard, href: '/dashboard' },
  { name: 'Accounts Directory', icon: Briefcase, href: '/accounts' },
  { name: 'Sales Pipeline & Levers', icon: TrendingUp, href: '/pipeline' },
  { name: 'AI Intelligence Assistant', icon: Brain, href: '/intelligence' },
  { name: 'System Settings & Config', icon: Settings, href: '/settings' },
]

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      setQuery('')
    }
  }, [isOpen])

  // Global key listener for Escape and Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const filteredAccounts = searchableAccounts.filter((a) =>
    a.name.toLowerCase().includes(query.toLowerCase())
  )

  const filteredNav = navigationItems.filter((n) =>
    n.name.toLowerCase().includes(query.toLowerCase())
  )

  const handleSelect = (href: string) => {
    router.push(href)
    onClose()
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/75 backdrop-blur-sm"
        />

        {/* Command Box Card */}
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Global Search Command Palette"
          initial={{ scale: 0.95, opacity: 0, y: -10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: -10 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
          className="relative w-full max-w-xl bg-card border border-border rounded-xl shadow-modal overflow-hidden z-50 text-foreground"
        >
          {/* Input Header */}
          <div className="flex items-center border-b border-border px-4 py-3">
            <Search className="w-4 h-4 text-muted-foreground mr-3 shrink-0" aria-hidden="true" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type an account name or page command (e.g., 'Acme', 'Pipeline')..."
              aria-label="Search accounts or navigate pages"
              className="flex-1 bg-transparent text-sm placeholder-muted-foreground focus:outline-none text-foreground"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                aria-label="Clear search query"
                className="p-1 hover:bg-secondary rounded text-muted-foreground mr-2"
              >
                <X className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            )}
            <kbd className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold text-muted-foreground bg-secondary/60 border border-border px-1.5 py-0.5 rounded font-mono">
              <Command className="w-3 h-3" /> K
            </kbd>
          </div>

          {/* Results List */}
          <div className="max-h-96 overflow-y-auto p-2 space-y-4">
            {/* Accounts Section */}
            {filteredAccounts.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-3 py-1.5 font-mono">
                  Accounts ({filteredAccounts.length})
                </p>
                <div className="space-y-0.5">
                  {filteredAccounts.map((account) => (
                    <button
                      key={account.name}
                      onClick={() => handleSelect(account.href)}
                      className="w-full flex items-center justify-between px-3 py-2 text-left rounded-md text-xs hover:bg-primary/10 hover:text-primary transition-colors group"
                    >
                      <div className="flex items-center gap-2.5">
                        <Briefcase className="w-4 h-4 text-muted-foreground group-hover:text-primary" aria-hidden="true" />
                        <span className="font-semibold text-foreground group-hover:text-primary">{account.name}</span>
                        <span className="text-[10px] px-1.5 py-0.2 bg-secondary text-muted-foreground rounded">{account.tier}</span>
                      </div>
                      <span className={`text-[10px] font-mono font-bold ${account.health < 40 ? 'text-red-400' : 'text-emerald-400'}`}>
                        Health: {account.health}/100
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Navigation Section */}
            {filteredNav.length > 0 && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-3 py-1.5 font-mono">
                  Navigation Shortcuts
                </p>
                <div className="space-y-0.5">
                  {filteredNav.map((item) => (
                    <button
                      key={item.name}
                      onClick={() => handleSelect(item.href)}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-left rounded-md text-xs hover:bg-secondary/60 text-foreground transition-colors"
                    >
                      <item.icon className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                      <span>{item.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {filteredAccounts.length === 0 && filteredNav.length === 0 && (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No matching accounts or navigation commands found for "{query}"
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-border px-4 py-2 bg-secondary/30 flex justify-between items-center text-[10px] text-muted-foreground">
            <span>Press <kbd className="font-mono bg-secondary border border-border px-1 rounded">ESC</kbd> to exit</span>
            <span>APEX Intelligence Search</span>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
