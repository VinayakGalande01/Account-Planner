'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  Brain,
  Settings,
  Menu,
  X,
  LogOut,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Plus,
  MessageSquare,
  MoreVertical,
  Trash2,
  AlertTriangle,
  Database,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useSidebar } from '@/context/SidebarContext'
import { toast } from 'sonner'
import Image from 'next/image'

const navigation = [
  { name: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { name: 'Accounts', icon: Briefcase, href: '/accounts' },
  { name: 'Pipeline', icon: TrendingUp, href: '/pipeline' },
  { name: 'Intelligence', icon: Brain, href: '/intelligence' },
  { name: 'Settings', icon: Settings, href: '/settings' },
]

import { useFocusTrap } from '@/lib/useFocusTrap'

export function Sidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const { isSidebarOpen, toggleSidebar, setSidebarOpen } = useSidebar()
  const [isMobile, setIsMobile] = useState(false)

  // Detect mobile width for responsive animations
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname?.startsWith(href)
  }

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={toggleSidebar}
        aria-label={isSidebarOpen ? 'Close navigation sidebar' : 'Open navigation sidebar'}
        aria-expanded={isSidebarOpen}
        className="fixed top-4 left-4 z-40 md:hidden p-2 bg-secondary border border-border rounded-md text-foreground"
      >
        {isSidebarOpen ? (
          <X className="w-5 h-5" aria-hidden="true" />
        ) : (
          <Menu className="w-5 h-5" aria-hidden="true" />
        )}
      </button>

      {/* Sidebar */}
      <motion.div
        role="navigation"
        aria-label="Main sidebar navigation"
        initial={isMobile ? { x: -256 } : { width: 256 }}
        animate={
          isMobile
            ? { x: isSidebarOpen ? 0 : -256, width: 256 }
            : { x: 0, width: isSidebarOpen ? 256 : 0 }
        }
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className={`fixed left-0 top-0 h-screen bg-sidebar border-sidebar-border flex flex-col p-6 z-30 overflow-hidden md:static md:translate-x-0 ${
          isSidebarOpen ? 'border-r' : 'border-r-0 p-0 w-0'
        }`}
      >
        <div className="flex flex-col h-full w-[208px]">
          {/* Logo */}
          <motion.div
            animate={{ opacity: isSidebarOpen ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            className="mb-8 flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <div className="w-8 h-8">
                <Image
                  src="/logo.png"
                  alt="APEX Logo"
                  width={32}
                  height={32}
                  className="object-contain drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] brightness-125"
                  priority
                />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground leading-none">APEX</h1>
                <span className="text-[10px] text-muted-foreground mt-1 block">Account Planner</span>
              </div>
            </div>
            {/* Collapse button on desktop */}
            <button
              onClick={() => setSidebarOpen(false)}
              aria-label="Collapse sidebar"
              className="hidden md:flex p-1 hover:bg-secondary/60 text-muted-foreground hover:text-foreground rounded transition-colors"
            >
              <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            </button>
          </motion.div>

          {/* Navigation */}
          <nav className="space-y-1">
            {navigation.map((item) => (
              <motion.div
                key={item.name}
                animate={{ opacity: isSidebarOpen ? 1 : 0 }}
                transition={{ duration: 0.2 }}
                whileHover={{ x: 2 }}
              >
                <Link
                  href={item.href}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                    isActive(item.href)
                      ? 'text-primary bg-primary/10 border-l-2 border-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
                  }`}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  <span>{item.name}</span>
                </Link>
              </motion.div>
            ))}
          </nav>

          {/* User profile */}
          <motion.div
            animate={{ opacity: isSidebarOpen ? 1 : 0 }}
            transition={{ duration: 0.2 }}
            className="pt-4 border-t border-border flex items-center justify-between px-2 mt-auto"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-md bg-primary flex items-center justify-center text-primary-foreground font-semibold text-xs flex-shrink-0">
                {user?.name?.substring(0, 2).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0 pr-2">
                <p className="text-xs font-medium text-foreground truncate">
                  {user?.name || 'Loading...'}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.email || 'User'}
                </p>
              </div>
            </div>
            <button
              onClick={() => {
                logout()
                router.push('/')
              }}
              aria-label="Log out of account"
              className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors flex-shrink-0"
            >
              <LogOut className="w-4 h-4" aria-hidden="true" />
            </button>
          </motion.div>
        </div>
      </motion.div>
    </>
  )
}
