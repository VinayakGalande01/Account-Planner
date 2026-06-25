'use client'

import { motion } from 'framer-motion'
import { usePathname } from 'next/navigation'
import { Bell, Search, ChevronRight } from 'lucide-react'

export function Header() {
  const pathname = usePathname()

  const getBreadcrumb = () => {
    if (pathname === '/') return { page: 'Dashboard', subtitle: 'Account Health' }
    if (pathname?.startsWith('/accounts')) return { page: 'Accounts', subtitle: 'Account Directory' }
    if (pathname?.startsWith('/pipeline')) return { page: 'Pipeline', subtitle: 'Sales Progress & Speed' }
    if (pathname?.startsWith('/intelligence')) return { page: 'Intelligence', subtitle: 'AI Assistant' }
    if (pathname?.startsWith('/settings')) return { page: 'Settings', subtitle: 'System Configuration' }
    return { page: 'Dashboard', subtitle: 'Welcome' }
  }

  const { page, subtitle } = getBreadcrumb()

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-background border-b border-border sticky top-0 z-20"
    >
      <div className="px-6 py-3.5 flex items-center justify-between gap-4">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">APEX</span>
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
          <span className="text-foreground font-medium">{subtitle}</span>
        </div>

        {/* Right section */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative hidden md:block w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Search accounts..."
              className="w-full bg-secondary border border-border rounded-md pl-9 pr-4 py-1.5 text-sm placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors"
            />
          </div>

          {/* Notification bell */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.98 }}
            className="relative p-2 hover:bg-secondary rounded-md transition-colors duration-200"
          >
            <Bell className="w-4 h-4 text-foreground" />
            <motion.div
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ repeat: Infinity, duration: 3 }}
              className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-destructive rounded-full"
            />
          </motion.button>
        </div>
      </div>
    </motion.header>
  )
}
