'use client'

// NotificationDropdown: header bell popover listing account risk/pipeline
// notifications with read/unread state.
// Major sections:
// - Mock notification data + types
// - State/hooks: notifications list, mark-all-read handler
// - Render: header, scrollable list, footer link

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, TrendingDown, CheckCircle2, X } from 'lucide-react'
import Link from 'next/link'

interface Notification {
  id: string
  title: string
  description: string
  time: string
  type: 'critical' | 'warning' | 'info'
  link: string
  read: boolean
}

const initialNotifications: Notification[] = [
  {
    id: '1',
    title: 'Critical Health Drop',
    description: 'Solace Health health score dropped to 18/100. Single-threaded sponsor risk flagged.',
    time: '10m ago',
    type: 'critical',
    link: '/accounts',
    read: false,
  },
  {
    id: '2',
    title: 'Stalled Pipeline Deal',
    description: 'Acme Corp renewal deal ($2.1M ARR) has stalled in Value Proposition stage for 21 days.',
    time: '1h ago',
    type: 'warning',
    link: '/pipeline',
    read: false,
  },
  {
    id: '3',
    title: 'Competitor Intrusion Detected',
    description: 'Cyberdyne Systems reported active competitor eval from Competitor X on LinkedIn.',
    time: '3h ago',
    type: 'warning',
    link: '/accounts',
    read: false,
  },
  {
    id: '4',
    title: 'AI Intelligence Sync',
    description: 'Weekly account velocity model trained successfully on latest CRM activity logs.',
    time: '1d ago',
    type: 'info',
    link: '/intelligence',
    read: true,
  },
]

interface NotificationDropdownProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificationDropdown({ isOpen, onClose }: NotificationDropdownProps) {
  // --- SECTION: State/Hooks ---
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications)

  if (!isOpen) return null

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const unreadCount = notifications.filter((n) => !n.read).length

  // --- SECTION: Render ---
  return (
    <AnimatePresence>
      <div className="absolute right-0 top-12 z-50 w-80 sm:w-96 bg-card border border-border rounded-xl shadow-popover overflow-hidden text-foreground">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/20">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
            {unreadCount > 0 && (
              <span className="px-1.5 py-0.5 bg-primary text-primary-foreground font-bold text-[10px] rounded-full font-mono">
                {unreadCount} new
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-[11px] font-semibold text-primary hover:underline"
              >
                Mark all as read
              </button>
            )}
            <button
              onClick={onClose}
              aria-label="Close notifications popover"
              className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-border/50">
          {notifications.map((n) => (
            <Link
              key={n.id}
              href={n.link}
              onClick={onClose}
              className={`block p-3.5 transition-colors hover:bg-secondary/40 ${
                !n.read ? 'bg-primary/5' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0">
                  {n.type === 'critical' && <AlertTriangle className="w-4 h-4 text-red-500" aria-hidden="true" />}
                  {n.type === 'warning' && <TrendingDown className="w-4 h-4 text-amber-500" aria-hidden="true" />}
                  {n.type === 'info' && <CheckCircle2 className="w-4 h-4 text-emerald-500" aria-hidden="true" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <p className={`text-xs font-semibold ${!n.read ? 'text-foreground font-bold' : 'text-muted-foreground'}`}>
                      {n.title}
                    </p>
                    <span className="text-[10px] text-muted-foreground font-mono shrink-0">{n.time}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                    {n.description}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-border p-2 bg-secondary/20 text-center">
          <Link
            href="/dashboard"
            onClick={onClose}
            className="text-[11px] font-semibold text-primary hover:underline block"
          >
            View all account risk triages
          </Link>
        </div>
      </div>
    </AnimatePresence>
  )
}
