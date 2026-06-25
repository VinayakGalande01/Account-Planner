'use client'

import { motion } from 'framer-motion'
import { useRouter, usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  Brain,
  Settings,
  Menu,
  X,
  LogOut,
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import Image from 'next/image'

const navigation = [
  { name: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { name: 'Accounts', icon: Briefcase, href: '/accounts' },
  { name: 'Pipeline', icon: TrendingUp, href: '/pipeline' },
  { name: 'Intelligence', icon: Brain, href: '/intelligence' },
  { name: 'Settings', icon: Settings, href: '/settings' },
]

export function Sidebar() {
  const [isOpen, setIsOpen] = useState(true)
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname?.startsWith(href)
  }

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-40 md:hidden"
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <Menu className="w-6 h-6" />
        )}
      </button>

      {/* Sidebar */}
      <motion.div
        initial={{ x: -300 }}
        animate={{ x: isOpen ? 0 : -300 }}
        transition={{ duration: 0.3 }}
        className="fixed left-0 top-0 h-screen w-64 bg-sidebar border-r border-sidebar-border flex flex-col p-6 z-30 md:static md:translate-x-0"
      >
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="mb-10"
        >
          <div className="flex items-center gap-2">
            <div className="w-8 h-8">
              <Image src="/logo.png" alt="APEX Logo" width={32} height={32} className="object-contain drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] brightness-125" priority />
            </div>
            <h1 className="text-lg font-semibold text-foreground">APEX</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-2 leading-tight">
            Account Planning
          </p>
        </motion.div>

        {/* Navigation */}
        <nav className="space-y-1 flex-1">
          {navigation.map((item, index) => (
            <motion.button
              key={item.name}
              onClick={() => router.push(item.href)}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + index * 0.04 }}
              whileHover={{ x: 2 }}
              className={`w-full flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                isActive(item.href)
                  ? 'text-primary bg-primary/10 border-l-2 border-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
              }`}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.name}</span>
            </motion.button>
          ))}
        </nav>

        {/* User profile */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="pt-4 border-t border-border flex items-center justify-between px-2"
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
            className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors flex-shrink-0"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </motion.div>
      </motion.div>
    </>
  )
}
