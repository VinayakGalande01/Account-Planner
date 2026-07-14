'use client'

import { motion, AnimatePresence } from 'framer-motion'
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
  { name: 'Golden Dataset', icon: Database, href: '/datasets' },
  { name: 'Settings', icon: Settings, href: '/settings' },
]


export function Sidebar() {
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const {
    isSidebarOpen,
    toggleSidebar,
    setSidebarOpen,
    activeSessionId,
    setActiveSessionId,
    sessions,
    loadSessions,
    createSession,
    deleteSession,
  } = useSidebar()

  const [isHistoryExpanded, setIsHistoryExpanded] = useState(true)
  const [dropdownSessionId, setDropdownSessionId] = useState<string | null>(null)
  const [sessionToDelete, setSessionToDelete] = useState<any | null>(null)
  const [isMobile, setIsMobile] = useState(false)

  // Detect mobile width for responsive animations
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Refresh sessions when component mounts
  useEffect(() => {
    if (user) {
      loadSessions()
    }
  }, [user])

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname?.startsWith(href)
  }

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-40 md:hidden p-2 bg-secondary border border-border rounded-md text-foreground"
      >
        {isSidebarOpen ? (
          <X className="w-5 h-5" />
        ) : (
          <Menu className="w-5 h-5" />
        )}
      </button>

      {/* Sidebar */}
      <motion.div
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
            initial={{ opacity: 0 }}
            animate={{ opacity: isSidebarOpen ? 1 : 0 }}
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
              className="hidden md:flex p-1 hover:bg-secondary/60 text-muted-foreground hover:text-foreground rounded transition-colors"
              title="Collapse Sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          </motion.div>

          {/* Navigation */}
          <nav className="space-y-1">
            {navigation.map((item, index) => (
              <motion.button
                key={item.name}
                onClick={() => router.push(item.href)}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: isSidebarOpen ? 1 : 0, x: isSidebarOpen ? 0 : -20 }}
                transition={{ delay: 0.05 + index * 0.03 }}
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

          {/* Divider */}
          <hr className="my-4 border-sidebar-border opacity-50" />

          {/* Chat History Collapsible Accordion */}
          <div className="flex flex-col flex-1 min-h-0">
            <div className="flex items-center justify-between px-2 mb-2">
              <button
                onClick={() => setIsHistoryExpanded(!isHistoryExpanded)}
                className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
              >
                {isHistoryExpanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                <span>Chat History</span>
              </button>

              {/* New Chat Button */}
              <button
                onClick={() => {
                  createSession()
                  router.push('/intelligence')
                }}
                className="p-1 hover:bg-secondary/60 text-muted-foreground hover:text-foreground rounded transition-colors"
                title="New Chat"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Chat Sessions list */}
            {isHistoryExpanded && (
              <div className="flex-1 overflow-y-auto space-y-0.5 pr-1 scrollbar-thin select-none">
                {sessions.length === 0 ? (
                  <div className="text-[11px] text-muted-foreground/60 px-2 py-2 italic">
                    No history
                  </div>
                ) : (
                  sessions.map((session) => (
                    <div
                      key={session.id}
                      className={`relative w-full rounded-md text-xs transition-colors flex items-center group ${
                        activeSessionId === session.id
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/40'
                      }`}
                    >
                      <button
                        onClick={() => {
                          setActiveSessionId(session.id)
                          router.push('/intelligence')
                        }}
                        className="flex-1 text-left px-2 py-1.5 truncate flex items-center gap-2 min-w-0"
                      >
                        <MessageSquare className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
                        <span className="truncate flex-1 pr-4">{session.title}</span>
                      </button>

                      {/* Three-dots menu button */}
                      <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setDropdownSessionId(dropdownSessionId === session.id ? null : session.id)
                          }}
                          className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground transition-colors"
                          title="Options"
                        >
                          <MoreVertical className="w-3.5 h-3.5" />
                        </button>
                        
                        {/* Dropdown Menu */}
                        {dropdownSessionId === session.id && (
                          <>
                            <div 
                              className="fixed inset-0 z-40" 
                              onClick={() => setDropdownSessionId(null)}
                            />
                            <div className="absolute right-0 mt-1 w-24 bg-[#1f1f2e] border border-border rounded-md shadow-lg py-1 z-50 animate-in fade-in slide-in-from-top-1 duration-100">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setDropdownSessionId(null)
                                  setSessionToDelete(session)
                                }}
                                className="w-full text-left px-2 py-1.5 text-xs text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors flex items-center gap-1.5"
                              >
                                <Trash2 className="w-3 h-3" />
                                <span>Delete</span>
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* User profile */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: isSidebarOpen ? 1 : 0 }}
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
              className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors flex-shrink-0"
              title="Log Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </motion.div>
        </div>
      </motion.div>

      {/* Custom Deletion Confirmation Modal */}
      <AnimatePresence>
        {sessionToDelete && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSessionToDelete(null)}
              className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            />

            {/* Modal Dialog Card */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="relative w-full max-w-md bg-[#181824] border border-border/80 rounded-xl p-6 shadow-2xl z-50 text-foreground"
            >
              <div className="flex gap-4 items-start">
                <div className="p-3 bg-red-500/10 rounded-full text-red-500 flex-shrink-0 animate-pulse">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">
                    Delete Chat History?
                  </h3>
                  <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                    Are you sure you want to permanently delete the conversation <span className="text-foreground font-semibold">"{sessionToDelete.title}"</span>? This will permanently delete it from the database and cannot be undone.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => setSessionToDelete(null)}
                  className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/40 rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    const toDeleteId = sessionToDelete.id
                    setSessionToDelete(null)
                    const success = await deleteSession(toDeleteId)
                    if (success) {
                      toast.success("Chat deleted successfully")
                    } else {
                      toast.error("Failed to delete chat")
                    }
                  }}
                  className="px-4 py-2 text-xs font-medium bg-red-500 hover:bg-red-600 text-white rounded-md shadow-lg shadow-red-500/15 transition-colors"
                >
                  Delete Permanently
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
