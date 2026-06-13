'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, AlertTriangle, Lightbulb, Zap, X, Terminal, ArrowRight, Activity, Sparkles } from 'lucide-react';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';


interface Insight {
  id: string;
  type: 'critical' | 'warning' | 'opportunity';
  title: string;
  description: string;
  targetAccount: string;
  targetAccountId: string;
  suggestedAction: string;
}

interface InsightsData {
  insights: Insight[];
  pipeline_quality_score: number;
  briefing: string;
}

interface ProactiveInsightsProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ProactiveInsights({ isOpen, onClose }: ProactiveInsightsProps) {
  const { setAiCommand, setActiveTab } = useData();
  const { authFetch } = useAuth();
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchInsights = async () => {
    setLoading(true);
    try {
      const res = await authFetch('/api/insights');
      const json = await res.json();
      setData(json);

    } catch (err) {
      console.error('Failed to fetch insights', err);
      // Fallback fallback mock data
      setData({
        pipeline_quality_score: 75,
        briefing: 'Pipeline reflects moderate velocity. Attention required on high-value single-threaded opportunities in negotiation. High CSAT scores on Strategic Tier indicate immediate upsell expansion possibilities.',
        insights: [
          {
            id: 'ins-1',
            type: 'critical',
            title: 'Critical Support Ticket',
            description: 'DataOsis (ACC-001) has an unresolved critical case: "Database sync failure on production". Ticket open 3 days. CSAT risk elevated.',
            targetAccount: 'DataOsis',
            targetAccountId: 'ACC-001',
            suggestedAction: 'Escalate case to engineering lead and trigger service recovery response.'
          },
          {
            id: 'ins-2',
            type: 'warning',
            title: 'Single-Threaded Deal Risk',
            description: 'Apex Systems (ACC-003) deal "APEX Cloud Expansion" ($420K) is in Negotiation with only one contact mapped.',
            targetAccount: 'Apex Systems',
            targetAccountId: 'ACC-003',
            suggestedAction: 'Engage security engineering head and procurement contact to secure signatures.'
          },
          {
            id: 'ins-3',
            type: 'opportunity',
            title: 'Expansion Catalyst',
            description: 'CloudScale Corp (ACC-002) reports a perfect 5.0 CSAT but has no active pipeline open. High potential for expansion.',
            targetAccount: 'CloudScale Corp',
            targetAccountId: 'ACC-002',
            suggestedAction: 'Draft QBR agenda focused on API scaling needs and present upsell proposal.'
          }
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchInsights();
    }
  }, [isOpen]);

  const handleRemediate = (insight: Insight) => {
    const prompt = `Perform pipeline remediation for account ${insight.targetAccount}. Issue: ${insight.title}. Details: ${insight.description} Action needed: ${insight.suggestedAction}`;
    setAiCommand(prompt);
    setActiveTab('Intelligence');
    onClose();
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-500 border-emerald-500/20';
    if (score >= 60) return 'text-amber-500 border-amber-500/20';
    return 'text-red-500 border-red-500/20';
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'critical':
        return <ShieldAlert className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case 'opportunity':
        return <Lightbulb className="w-4 h-4 text-primary" />;
      default:
        return <Zap className="w-4 h-4 text-zinc-400" />;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-[#000] z-40 xl:hidden"
          />

          {/* Sliding Panel */}
          <motion.div
            initial={{ x: '100%', opacity: 0.95 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.95 }}
            transition={{ type: 'spring', damping: 26, stiffness: 220 }}
            className="fixed right-0 top-0 bottom-0 w-80 md:w-96 bg-[#040405] border-l border-white/[0.04] z-50 flex flex-col overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.8)]"
          >
            {/* Tactical Grid Scan Overlay */}
            <div className="absolute inset-0 scanlines pointer-events-none opacity-20" />

            {/* Header */}
            <div className="px-5 py-4 border-b border-white/[0.04] bg-white/[0.01] flex items-center justify-between shrink-0 relative z-10">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary animate-pulse" />
                <h3 className="text-[13px] font-black uppercase tracking-[0.25em] text-foreground font-[family-name:var(--font-mono)]">
                  Key Account Insights
                </h3>
              </div>
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/[0.04] rounded text-zinc-500 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6 scrollbar-tactical relative z-10">
              {loading ? (
                <div className="h-full flex flex-col items-center justify-center space-y-4 py-20 text-center">
                  <div className="relative w-12 h-12 flex items-center justify-center">
                    <Activity className="w-6 h-6 text-primary animate-pulse" />
                    <div className="absolute inset-0 w-12 h-12 rounded-full border border-primary/20 border-t-primary animate-spin" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-[12px] font-black uppercase tracking-[0.2em] text-zinc-500 font-[family-name:var(--font-mono)]">
                      Updating Insights...
                    </p>
                    <p className="text-[11px] font-bold text-zinc-700 font-[family-name:var(--font-mono)]">
                      Analyzing account lists and sales progress
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  {/* Pipeline Quality Score Card */}
                  {data && (
                    <div className="corner-brackets p-4 bg-white/[0.01] rounded">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-black text-zinc-500 uppercase tracking-widest font-[family-name:var(--font-mono)]">
                            Pipeline Score
                          </p>
                          <h4 className="text-[13px] font-black text-foreground uppercase tracking-wider font-[family-name:var(--font-mono)] mt-0.5">
                            Overall Health Score
                          </h4>
                        </div>
                        <div className={`px-2.5 py-1.5 rounded border text-base font-black font-[family-name:var(--font-mono)] ${getScoreColor(data.pipeline_quality_score)}`}>
                          {data.pipeline_quality_score}/100
                        </div>
                      </div>
                      
                      {/* Bar indicator */}
                      <div className="h-[4px] bg-white/[0.02] rounded-full overflow-hidden mt-3">
                        <div 
                          className={`h-full rounded-full transition-all duration-1000 ${
                            data.pipeline_quality_score >= 80 ? 'bg-emerald-500' : data.pipeline_quality_score >= 60 ? 'bg-amber-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${data.pipeline_quality_score}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* AI Strategic Briefing */}
                  {data?.briefing && (
                    <div className="space-y-2">
                      <h4 className="text-[12px] font-black text-zinc-500 uppercase tracking-[0.2em] font-[family-name:var(--font-mono)]">
                        AI Brief Summary
                      </h4>
                      <div className="glass-card p-4 border border-primary/10 relative overflow-hidden bg-primary/[0.01]">
                        <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
                        <p className="text-[13px] font-[family-name:var(--font-mono)] text-zinc-300 leading-relaxed">
                          {data.briefing}
                        </p>
                        <div className="flex items-center gap-1.5 mt-3 text-[11px] font-black text-primary uppercase tracking-widest font-[family-name:var(--font-mono)]">
                          <Terminal className="w-3 h-3" />
                          <span>Generated by AI Assistant</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Anomalies List */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[12px] font-black text-zinc-500 uppercase tracking-[0.2em] font-[family-name:var(--font-mono)]">
                        Sales Issues ({data?.insights?.length || 0})
                      </h4>
                      <button 
                        onClick={fetchInsights}
                        className="text-[11px] font-black text-primary uppercase tracking-widest hover:underline font-[family-name:var(--font-mono)]"
                      >
                        Scan now
                      </button>
                    </div>

                    <div className="space-y-3.5">
                      {data?.insights && data.insights.length > 0 ? (
                        data.insights.map((insight) => (
                          <div 
                            key={insight.id} 
                            className={`glass-card p-4 relative overflow-hidden border ${
                              insight.type === 'critical' 
                                ? 'border-red-500/10 hover:border-red-500/30' 
                                : insight.type === 'warning' 
                                ? 'border-amber-500/10 hover:border-amber-500/30' 
                                : 'border-primary/10 hover:border-primary/30'
                            } transition-all duration-200`}
                          >
                            {/* Accent indicator line */}
                            <div className={`absolute top-0 left-0 w-[2px] h-full ${
                              insight.type === 'critical' ? 'bg-red-500' : insight.type === 'warning' ? 'bg-amber-500' : 'bg-primary'
                            }`} />

                            <div className="flex items-start gap-2.5">
                              <div className="mt-0.5 shrink-0">
                                {getIcon(insight.type)}
                              </div>
                              <div className="space-y-1 flex-1 min-w-0">
                                <span className={`text-[11px] font-black uppercase tracking-widest font-[family-name:var(--font-mono)] ${
                                  insight.type === 'critical' ? 'text-red-500' : insight.type === 'warning' ? 'text-amber-500' : 'text-primary'
                                }`}>
                                  {insight.type}
                                </span>
                                <h5 className="text-[14px] font-black text-foreground uppercase tracking-wide truncate">
                                  {insight.title}
                                </h5>
                                <p className="text-[13px] text-zinc-400 leading-relaxed font-medium">
                                  {insight.description}
                                </p>
                                <div className="mt-3 pt-2.5 border-t border-white/[0.04] space-y-2">
                                  <p className="text-[12px] text-zinc-500 italic">
                                    <span className="font-bold uppercase tracking-wider text-zinc-600 font-[family-name:var(--font-mono)] block not-italic text-[11px] mb-0.5">Recommendation</span>
                                    {insight.suggestedAction}
                                  </p>
                                  <button
                                    onClick={() => handleRemediate(insight)}
                                    className="w-full flex items-center justify-between px-2.5 py-1.5 bg-white/[0.02] hover:bg-primary/10 border border-white/[0.04] hover:border-primary/20 rounded text-[12px] font-black uppercase tracking-widest text-zinc-400 hover:text-primary transition-all font-[family-name:var(--font-mono)] group"
                                  >
                                    <span>Fix This Issue</span>
                                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="py-10 text-center text-[13px] text-zinc-600 font-[family-name:var(--font-mono)] uppercase tracking-widest">
                          No pipeline anomalies active
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Sticky footer action */}
            <div className="p-4 border-t border-white/[0.04] bg-white/[0.01] shrink-0 relative z-10">
              <button
                onClick={() => {
                  setAiCommand('Run comprehensive pipeline health audit and diagnostic.');
                  setActiveTab('Intelligence');
                  onClose();
                }}
                className="w-full py-2.5 bg-primary hover:bg-primary/95 text-white flex items-center justify-center gap-2 rounded text-[13px] font-black uppercase tracking-[0.15em] transition-all font-[family-name:var(--font-mono)] shadow-[0_0_20px_rgba(37,99,235,0.2)] hover:shadow-[0_0_25px_rgba(37,99,235,0.35)] border border-primary/20"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>Run Detailed Analysis</span>
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
