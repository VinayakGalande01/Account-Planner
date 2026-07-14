'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from '@/components/Sidebar'
import { Header } from '@/components/header'
import { useAuth } from '@/context/AuthContext'
import { toast } from 'sonner'
import { 
  Database, 
  Search, 
  Plus, 
  Filter, 
  Trash2, 
  Edit3, 
  X, 
  AlertTriangle, 
  CheckCircle, 
  Sparkles, 
  Info,
  ChevronDown,
  Tag,
  Clock,
  Shield,
  Layers,
  ChevronRight
} from 'lucide-react'

interface GoldenTestCase {
  id: string
  version: number
  status: string
  source: string
  priority: string
  tags: string[]
  owner_id: number
  query: string
  user_context: Record<string, any>

  expected_intent: string
  expected_entities: Record<string, any>
  expected_confidence: string
  expected_retrieval_ids: Record<string, any>
  expected_retrieval_count: number | null
  expected_filter_keys: Record<string, any>
  expected_reasoning_confidence_min: number
  expected_key_findings: Record<string, any>
  expected_json_schema: Record<string, any>
  expected_narrative_keywords: string[]
  expected_recommendation_type: string | null
  expected_business_outcome: string | null
  expected_bis_category: string | null
  review_notes: string | null
  created_at: string
  updated_at: string
}

export default function GoldenDatasetPage() {
  const { authFetch } = useAuth()
  const [cases, setCases] = useState<GoldenTestCase[]>([])
  const [loading, setLoading] = useState(true)
  
  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedIntent, setSelectedIntent] = useState('ALL')
  const [selectedPriority, setSelectedPriority] = useState('ALL')
  const [selectedStatus, setSelectedStatus] = useState('ACTIVE')
  
  // Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [selectedCase, setSelectedCase] = useState<GoldenTestCase | null>(null)
  
  // Form State (Create & Edit)
  const [formQuery, setFormQuery] = useState('')
  const [formIntent, setFormIntent] = useState('risk_assessment')
  const [formPriority, setFormPriority] = useState('MEDIUM')
  const [formStatus, setFormStatus] = useState('ACTIVE')
  const [formTags, setFormTags] = useState('')
  const [formEntities, setFormEntities] = useState('{\n  "account": "Wipro"\n}')
  const [formRecType, setFormRecType] = useState('RISK_MITIGATION')
  const [formNotes, setFormNotes] = useState('')

  // Load dataset
  const loadDataset = async () => {
    setLoading(true)
    try {
      let url = '/api/eval/golden'
      const params = []
      if (selectedStatus !== 'ALL') params.push(`status=${selectedStatus}`)
      if (selectedPriority !== 'ALL') params.push(`priority=${selectedPriority}`)
      if (selectedIntent !== 'ALL') params.push(`intent=${selectedIntent}`)
      
      if (params.length > 0) {
        url += '?' + params.join('&')
      }
      
      const res = await authFetch(url)
      if (res.ok) {
        const data = await res.json()
        setCases(data)
      } else {
        toast.error('Failed to load golden dataset')
      }
    } catch (err) {
      console.error(err)
      toast.error('Connection failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDataset()
  }, [selectedIntent, selectedPriority, selectedStatus])

  // Filtered cases by search term client-side
  const filteredCases = cases.filter(c => 
    c.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.expected_intent.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.tags.some(t => t.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  // Quick stats
  const totalCount = cases.length
  const uniqueIntents = new Set(cases.map(c => c.expected_intent)).size
  const criticalCount = cases.filter(c => c.priority === 'CRITICAL').length
  const activeCount = cases.filter(c => c.status === 'ACTIVE').length

  const handleOpenDetail = (tc: GoldenTestCase) => {
    setSelectedCase(tc)
    setFormQuery(tc.query)
    setFormIntent(tc.expected_intent)
    setFormPriority(tc.priority)
    setFormStatus(tc.status)
    setFormTags(tc.tags.join(', '))
    setFormEntities(JSON.stringify(tc.expected_entities, null, 2))
    setFormRecType(tc.expected_recommendation_type || '')
    setFormNotes(tc.review_notes || '')
    setIsDetailModalOpen(true)
  }

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formQuery || !formIntent) {
      toast.error('Query and Expected Intent are required')
      return
    }

    let parsedEntities = {}
    try {
      if (formEntities.trim()) {
        parsedEntities = JSON.parse(formEntities)
      }
    } catch (err) {
      toast.error('Invalid JSON in Expected Entities')
      return
    }

    const payload = {
      query: formQuery,
      expected_intent: formIntent,
      expected_entities: parsedEntities,
      priority: formPriority,
      status: formStatus,
      tags: formTags.split(',').map(t => t.trim()).filter(t => t.length > 0),
      expected_recommendation_type: formRecType || null,
      review_notes: formNotes || null
    }

    try {
      const res = await authFetch('/api/eval/golden', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        toast.success('Golden testcase created successfully')
        setIsCreateModalOpen(false)
        resetForm()
        loadDataset()
      } else {
        toast.error('Failed to create testcase')
      }
    } catch (err) {
      console.error(err)
      toast.error('Request failed')
    }
  }

  const handleUpdateCase = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCase) return

    let parsedEntities = {}
    try {
      if (formEntities.trim()) {
        parsedEntities = JSON.parse(formEntities)
      }
    } catch (err) {
      toast.error('Invalid JSON in Expected Entities')
      return
    }

    const payload = {
      query: formQuery,
      expected_intent: formIntent,
      expected_entities: parsedEntities,
      priority: formPriority,
      status: formStatus,
      tags: formTags.split(',').map(t => t.trim()).filter(t => t.length > 0),
      expected_recommendation_type: formRecType || null,
      review_notes: formNotes || null
    }

    try {
      const res = await authFetch(`/api/eval/golden/${selectedCase.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (res.ok) {
        toast.success('Golden testcase updated (version incremented)')
        setIsDetailModalOpen(false)
        loadDataset()
      } else {
        toast.error('Failed to update testcase')
      }
    } catch (err) {
      console.error(err)
      toast.error('Request failed')
    }
  }

  const handleDeleteCase = async (tc: GoldenTestCase, hardDelete = false) => {
    const confirmMsg = hardDelete 
      ? `Are you sure you want to permanently delete this test case from the database?`
      : `Are you sure you want to deprecate/archive this test case?`

    if (!window.confirm(confirmMsg)) return

    try {
      const url = `/api/eval/golden/${tc.id}${hardDelete ? '?hard_delete=true' : ''}`
      const res = await authFetch(url, { method: 'DELETE' })
      
      if (res.ok) {
        toast.success(hardDelete ? 'Testcase deleted permanently' : 'Testcase deprecated/archived')
        setIsDetailModalOpen(false)
        loadDataset()
      } else {
        toast.error('Action failed')
      }
    } catch (err) {
      console.error(err)
      toast.error('Request failed')
    }
  }

  const resetForm = () => {
    setFormQuery('')
    setFormIntent('risk_assessment')
    setFormPriority('MEDIUM')
    setFormStatus('ACTIVE')
    setFormTags('')
    setFormEntities('{\n  "account": "Wipro"\n}')
    setFormRecType('RISK_MITIGATION')
    setFormNotes('')
    setSelectedCase(null)
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 flex flex-col md:ml-0 overflow-hidden">
        <Header />
        
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {/* Page Title & Stats */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h1 className="text-3xl font-semibold text-foreground flex items-center gap-2">
                <Database className="w-8 h-8 text-primary" />
                Golden Dataset
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                Manage the immutable ground-truth benchmark scenarios for pipeline evaluations
              </p>
            </motion.div>
            
            <motion.button
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => { resetForm(); setIsCreateModalOpen(true) }}
              className="bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Test Case
            </motion.button>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Total Scenarios', value: totalCount, icon: Layers, color: 'text-blue-400' },
              { label: 'Intents Covered', value: `${uniqueIntents}/8`, icon: Sparkles, color: 'text-purple-400' },
              { label: 'Critical Cases', value: criticalCount, icon: AlertTriangle, color: 'text-amber-400' },
              { label: 'Active Status', value: activeCount, icon: CheckCircle, color: 'text-emerald-400' },
            ].map((stat, idx) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="bg-secondary/10 border border-border/80 rounded-xl p-4 flex items-center justify-between shadow-sm backdrop-blur-sm"
              >
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-semibold mt-1 text-foreground">{stat.value}</p>
                </div>
                <stat.icon className={`w-6 h-6 ${stat.color} opacity-80`} />
              </motion.div>
            ))}
          </div>

          {/* Search & Filter Section */}
          <div className="bg-secondary/10 border border-border/80 rounded-xl p-4 mb-6 flex flex-col md:flex-row gap-4 items-center justify-between backdrop-blur-sm">
            <div className="relative w-full md:w-96">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search queries, intents, or tags..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
              />
            </div>
            
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground mr-1">
                <Filter className="w-3.5 h-3.5" />
                <span>Filters:</span>
              </div>
              
              {/* Intent Filter */}
              <select
                value={selectedIntent}
                onChange={(e) => setSelectedIntent(e.target.value)}
                className="bg-background border border-border text-foreground text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-primary"
              >
                <option value="ALL">All Intents</option>
                <option value="risk_assessment">Risk Assessment</option>
                <option value="opportunity_expansion">Opportunity Expansion</option>
                <option value="competitive_intelligence">Competitive Intelligence</option>
                <option value="relationship_analysis">Relationship Analysis</option>
                <option value="action_recommendation">Action Recommendation</option>
                <option value="pipeline_summary">Pipeline Summary</option>
                <option value="draft_email">Draft Email</option>
                <option value="meeting_agenda">Meeting Agenda</option>
              </select>

              {/* Priority Filter */}
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="bg-background border border-border text-foreground text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-primary"
              >
                <option value="ALL">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              {/* Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-background border border-border text-foreground text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-primary"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="DEPRECATED">Deprecated</option>
              </select>
            </div>
          </div>

          {/* Golden Cases Table/List */}
          {loading ? (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">Loading test cases...</p>
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-border/80 rounded-xl bg-secondary/5">
              <Database className="w-12 h-12 text-muted-foreground/60 mx-auto mb-4" />
              <h3 className="text-base font-semibold text-foreground">No test cases found</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                No golden cases match your search query and filters. Try adjusting your search parameters.
              </p>
            </div>
          ) : (
            <div className="bg-[#181824] border border-border/80 rounded-xl overflow-hidden shadow-lg">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border/60 bg-secondary/20 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    <th className="px-6 py-4">Query</th>
                    <th className="px-6 py-4">Expected Intent</th>
                    <th className="px-6 py-4">Priority</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Version</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40 text-sm text-foreground">
                  {filteredCases.map((tc) => (
                    <tr 
                      key={tc.id} 
                      className="hover:bg-secondary/10 transition-colors duration-150 cursor-pointer"
                      onClick={() => handleOpenDetail(tc)}
                    >
                      <td className="px-6 py-4 max-w-sm truncate font-medium">
                        {tc.query}
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-primary/10 text-primary border border-primary/20 text-xs px-2.5 py-1 rounded-md font-medium capitalize">
                          {tc.expected_intent.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-xs px-2.5 py-1 rounded-md font-semibold ${
                          tc.priority === 'CRITICAL' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                          tc.priority === 'HIGH' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                          tc.priority === 'MEDIUM' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                          'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                        }`}>
                          {tc.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          tc.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400' :
                          tc.status === 'UNDER_REVIEW' ? 'bg-amber-500/10 text-amber-400' :
                          'bg-slate-500/10 text-slate-400'
                        }`}>
                          ● {tc.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs">
                        v{tc.version}
                      </td>
                      <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleOpenDetail(tc)}
                            className="p-1.5 hover:bg-secondary/80 text-muted-foreground hover:text-foreground rounded-lg transition-colors"
                            title="Edit"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteCase(tc)}
                            className="p-1.5 hover:bg-secondary/80 text-muted-foreground hover:text-red-400 rounded-lg transition-colors"
                            title="Archive"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>

      {/* ────────────────── CREATE MODAL ────────────────── */}
      <AnimatePresence>
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsCreateModalOpen(false)}
              className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            />
            
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="relative w-full max-w-2xl bg-[#181824] border border-border rounded-xl shadow-2xl z-50 flex flex-col max-h-[85vh] text-foreground"
            >
              <div className="p-6 border-b border-border flex items-center justify-between">
                <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                  <Database className="w-5 h-5 text-primary" />
                  Add New Golden Test Case
                </h3>
                <button 
                  onClick={() => setIsCreateModalOpen(false)} 
                  className="p-1 hover:bg-secondary rounded-lg text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateCase} className="p-6 overflow-y-auto space-y-4 flex-1">
                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    User Query / Scenario Statement
                  </label>
                  <input
                    type="text"
                    required
                    value={formQuery}
                    onChange={(e) => setFormQuery(e.target.value)}
                    placeholder="e.g. Give me the action plan to unblock Wipro stuck deal"
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Expected Intent Class
                    </label>
                    <select
                      value={formIntent}
                      onChange={(e) => setFormIntent(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="risk_assessment">Risk Assessment</option>
                      <option value="opportunity_expansion">Opportunity Expansion</option>
                      <option value="competitive_intelligence">Competitive Intelligence</option>
                      <option value="relationship_analysis">Relationship Analysis</option>
                      <option value="action_recommendation">Action Recommendation</option>
                      <option value="pipeline_summary">Pipeline Summary</option>
                      <option value="draft_email">Draft Email</option>
                      <option value="meeting_agenda">Meeting Agenda</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Priority Level
                    </label>
                    <select
                      value={formPriority}
                      onChange={(e) => setFormPriority(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="CRITICAL">Critical (CI blocker)</option>
                      <option value="HIGH">High</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="LOW">Low</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Expected Recommendation Type
                    </label>
                    <select
                      value={formRecType}
                      onChange={(e) => setFormRecType(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="RISK_MITIGATION">Risk Mitigation</option>
                      <option value="GROWTH_STRATEGY">Growth Strategy</option>
                      <option value="COMPETITIVE_DEFENSE">Competitive Defense</option>
                      <option value="RELATIONSHIP_BUILDING">Relationship Building</option>
                      <option value="ACTION_PLAN">Action Plan</option>
                      <option value="PIPELINE_REVIEW">Pipeline Review</option>
                      <option value="EMAIL_DRAFT">Email Draft</option>
                      <option value="AGENDA_PREP">Agenda Prep</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Tags (comma separated)
                    </label>
                    <input
                      type="text"
                      value={formTags}
                      onChange={(e) => setFormTags(e.target.value)}
                      placeholder="e.g. risk, stuck_deal, Wipro"
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Expected Entities JSON
                  </label>
                  <textarea
                    rows={4}
                    value={formEntities}
                    onChange={(e) => setFormEntities(e.target.value)}
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Review / Architect Notes
                  </label>
                  <textarea
                    rows={2}
                    value={formNotes}
                    onChange={(e) => setFormNotes(e.target.value)}
                    placeholder="Document baseline context or reasons why this edge case is added"
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                  />
                </div>

                <div className="pt-4 border-t border-border flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium shadow-md"
                  >
                    Create Test Case
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ────────────────── DETAIL/EDIT MODAL ────────────────── */}
      <AnimatePresence>
        {isDetailModalOpen && selectedCase && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsDetailModalOpen(false)}
              className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            />
            
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="relative w-full max-w-2xl bg-[#181824] border border-border rounded-xl shadow-2xl z-50 flex flex-col max-h-[85vh] text-foreground"
            >
              <div className="p-6 border-b border-border flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                    <Database className="w-5 h-5 text-primary" />
                    Review/Modify Golden Case
                  </h3>
                  <span className="text-xs text-muted-foreground font-mono mt-0.5 block">
                    ID: {selectedCase.id} | version: v{selectedCase.version}
                  </span>
                </div>
                <button 
                  onClick={() => setIsDetailModalOpen(false)} 
                  className="p-1 hover:bg-secondary rounded-lg text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleUpdateCase} className="p-6 overflow-y-auto space-y-4 flex-1">
                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    User Query / Scenario Statement
                  </label>
                  <input
                    type="text"
                    required
                    value={formQuery}
                    onChange={(e) => setFormQuery(e.target.value)}
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Intent Class
                    </label>
                    <select
                      value={formIntent}
                      onChange={(e) => setFormIntent(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="risk_assessment">Risk Assessment</option>
                      <option value="opportunity_expansion">Opportunity Expansion</option>
                      <option value="competitive_intelligence">Competitive Intelligence</option>
                      <option value="relationship_analysis">Relationship Analysis</option>
                      <option value="action_recommendation">Action Recommendation</option>
                      <option value="pipeline_summary">Pipeline Summary</option>
                      <option value="draft_email">Draft Email</option>
                      <option value="meeting_agenda">Meeting Agenda</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Priority Level
                    </label>
                    <select
                      value={formPriority}
                      onChange={(e) => setFormPriority(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="CRITICAL">Critical (CI blocker)</option>
                      <option value="HIGH">High</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="LOW">Low</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Status Flag
                    </label>
                    <select
                      value={formStatus}
                      onChange={(e) => setFormStatus(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="ACTIVE">Active</option>
                      <option value="UNDER_REVIEW">Under Review</option>
                      <option value="DEPRECATED">Deprecated</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Recommendation Type
                    </label>
                    <select
                      value={formRecType}
                      onChange={(e) => setFormRecType(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground text-sm"
                    >
                      <option value="RISK_MITIGATION">Risk Mitigation</option>
                      <option value="GROWTH_STRATEGY">Growth Strategy</option>
                      <option value="COMPETITIVE_DEFENSE">Competitive Defense</option>
                      <option value="RELATIONSHIP_BUILDING">Relationship Building</option>
                      <option value="ACTION_PLAN">Action Plan</option>
                      <option value="PIPELINE_REVIEW">Pipeline Review</option>
                      <option value="EMAIL_DRAFT">Email Draft</option>
                      <option value="AGENDA_PREP">Agenda Prep</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                      Tags (comma separated)
                    </label>
                    <input
                      type="text"
                      value={formTags}
                      onChange={(e) => setFormTags(e.target.value)}
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Expected Entities JSON
                  </label>
                  <textarea
                    rows={4}
                    value={formEntities}
                    onChange={(e) => setFormEntities(e.target.value)}
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Review / Architect Notes
                  </label>
                  <textarea
                    rows={2}
                    value={formNotes}
                    onChange={(e) => setFormNotes(e.target.value)}
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-foreground"
                  />
                </div>

                <div className="pt-4 border-t border-border flex items-center justify-between">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleDeleteCase(selectedCase)}
                      className="bg-slate-500/10 hover:bg-slate-500/20 text-slate-400 border border-slate-500/20 px-3 py-2 rounded-lg text-xs font-medium"
                      title="Set status to DEPRECATED"
                    >
                      Deprecate
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteCase(selectedCase, true)}
                      className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-3 py-2 rounded-lg text-xs font-medium"
                      title="Permanently remove from DB"
                    >
                      Permanently Delete
                    </button>
                  </div>
                  
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setIsDetailModalOpen(false)}
                      className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium shadow-md"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
