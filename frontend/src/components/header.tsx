'use client'

// Header: sticky top app bar with breadcrumb, global search trigger
// (Cmd/Ctrl+K), and notifications bell, wiring CommandPalette and
// NotificationDropdown.
// Major sections:
// - State/hooks + global keydown listener + breadcrumb resolver
// - Render: breadcrumb nav, search trigger, notification bell, modals

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { usePathname } from 'next/navigation'
import { Bell, Search, ChevronRight, Menu, Command } from 'lucide-react'
import { useSidebar } from '@/context/SidebarContext'
import { CommandPalette } from '@/components/CommandPalette'
import { NotificationDropdown } from '@/components/NotificationDropdown'

export function Header() {
  // --- SECTION: State/Hooks ---
  const pathname = usePathname()
  const { isSidebarOpen, setSidebarOpen } = useSidebar()
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)

  // Listen for global Cmd+K or Ctrl+K keypress
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const getBreadcrumb = () => {
    if (pathname === '/') return { page: 'Dashboard', subtitle: 'Account Health' }
    if (pathname?.startsWith('/accounts')) return { page: 'Accounts', subtitle: 'Account Directory' }
    if (pathname?.startsWith('/pipeline')) return { page: 'Pipeline', subtitle: 'Sales Progress & Speed' }
    if (pathname?.startsWith('/intelligence')) return { page: 'Intelligence', subtitle: 'AI Assistant' }
    if (pathname?.startsWith('/settings')) return { page: 'Settings', subtitle: 'System Configuration' }
    if (pathname?.startsWith('/datasets')) return { page: 'Golden Dataset', subtitle: 'QA Benchmark Scenarios' }
    return { page: 'Dashboard', subtitle: 'Welcome' }
  }

  const { page, subtitle } = getBreadcrumb()

  // --- SECTION: Render ---
  return (
    <>
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="bg-background border-b border-border sticky top-0 z-20"
      >
        <div className="px-6 py-3.5 flex items-center justify-between gap-4">
          {/* Breadcrumbs */}
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs">
            {!isSidebarOpen && (
              <motion.button
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                onClick={() => setSidebarOpen(true)}
                aria-label="Expand navigation sidebar"
                className="mr-2 p-1.5 hover:bg-secondary/80 text-muted-foreground hover:text-foreground rounded-md transition-colors flex items-center justify-center"
              >
                <Menu className="w-4.5 h-4.5" aria-hidden="true" />
              </motion.button>
            )}
            <ol className="flex items-center gap-2">
              <li className="text-muted-foreground">APEX</li>
              <li aria-hidden="true"><ChevronRight className="w-3 h-3 text-muted-foreground" /></li>
              <li className="text-foreground font-medium" aria-current="page">{subtitle}</li>
            </ol>
          </nav>

          {/* Right section */}
          <div className="flex items-center gap-3 relative">
            {/* Search Trigger */}
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              aria-label="Open command palette search"
              className="relative hidden md:flex items-center justify-between w-64 bg-secondary border border-border rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:border-primary/50 hover:text-foreground transition-all"
            >
              <div className="flex items-center gap-2">
                <Search className="w-3.5 h-3.5 text-muted-foreground" aria-hidden="true" />
                <span>Search accounts...</span>
              </div>
              <kbd className="inline-flex items-center gap-0.5 text-[10px] font-mono bg-background border border-border px-1.5 py-0.5 rounded text-muted-foreground">
                <Command className="w-3 h-3" aria-hidden="true" /> K
              </kbd>
            </button>

            {/* Notification Bell Trigger */}
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              aria-label="Open notifications dropdown"
              aria-expanded={isNotificationsOpen}
              className="relative p-2 hover:bg-secondary rounded-md transition-colors duration-200"
            >
              <Bell className="w-4 h-4 text-foreground" aria-hidden="true" />
              <span className="sr-only">Notifications feed</span>
              <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-destructive rounded-full" />
            </motion.button>

            {/* Notification Popover */}
            <NotificationDropdown
              isOpen={isNotificationsOpen}
              onClose={() => setIsNotificationsOpen(false)}
            />
          </div>
        </div>
      </motion.header>

      {/* Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </>
  )
}
