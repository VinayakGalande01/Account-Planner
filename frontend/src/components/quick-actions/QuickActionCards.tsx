'use client';

import React, { useState } from 'react';

// ==========================================
// 1. Executive Email Card
// ==========================================
interface ExecEmailData {
  subject: string;
  body: string;
  suggested_recipients: Array<{ name: string; role: string }>;
  send_later_hint?: string;
}

export function ExecEmailCard({ data }: { data: ExecEmailData }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const textToCopy = `Subject: ${data.subject}\n\n${data.body}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">✉️</span>
          <h3 className="font-bold text-zinc-900 dark:text-zinc-50 text-md">Generated Executive Email</h3>
        </div>
        <button
          onClick={handleCopy}
          className="text-xs bg-primary text-primary-foreground font-semibold px-3 py-1.5 rounded-lg hover:opacity-90 active:scale-95 transition-all shadow-sm flex items-center gap-1.5"
        >
          {copied ? '✅ Copied' : '📋 Copy Draft'}
        </button>
      </div>

      {data.suggested_recipients && data.suggested_recipients.length > 0 && (
        <div className="text-xs text-zinc-500 dark:text-zinc-400 space-y-1">
          <span className="font-semibold text-zinc-700 dark:text-zinc-300">Suggested Recipients: </span>
          {data.suggested_recipients.map((r, i) => (
            <span key={i} className="inline-block bg-zinc-200/60 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 px-2 py-0.5 rounded-full mr-1.5">
              {r.name} ({r.role})
            </span>
          ))}
        </div>
      )}

      <div className="space-y-1.5">
        <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Subject</div>
        <div className="p-3 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm text-zinc-900 dark:text-zinc-100 font-medium">
          {data.subject}
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Body</div>
        <div className="p-4 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap leading-relaxed">
          {data.body}
        </div>
      </div>

      {data.send_later_hint && (
        <div className="bg-amber-500/10 border-l-4 border-l-amber-500 dark:border-l-amber-600 p-3 rounded-r-xl flex gap-2 text-xs text-amber-800 dark:text-amber-400 leading-normal">
          <span className="flex-shrink-0 text-sm">💡</span>
          <span><strong>Sending Strategy:</strong> {data.send_later_hint}</span>
        </div>
      )}
    </div>
  );
}

// ==========================================
// 2. Meeting Agenda Card
// ==========================================
interface AgendaItem {
  order: number;
  title: string;
  duration_min: number;
  owner: string;
  talking_points: string[];
  why_this_matters: string;
}

interface MeetingAgendaData {
  meeting_title: string;
  audience_type: string;
  duration_minutes: number;
  agenda_items: AgendaItem[];
  prep_checklist: string[];
  suggested_attendees: Array<{ name: string; role: string }>;
}

export function MeetingAgendaCard({ data }: { data: MeetingAgendaData }) {
  return (
    <div className="border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl p-5 shadow-sm space-y-5">
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">📅</span>
          <div>
            <h3 className="font-bold text-zinc-900 dark:text-zinc-50 text-md">{data.meeting_title}</h3>
            <p className="text-xs text-zinc-500">Audience Focus: <span className="font-semibold text-primary">{data.audience_type}</span> • Total: {data.duration_minutes} min</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Agenda Schedule</div>
        <div className="space-y-3">
          {data.agenda_items.map((item, i) => (
            <div key={i} className="flex gap-4 border-l-2 border-l-primary/30 pl-4 relative">
              <div className="absolute w-2.5 h-2.5 rounded-full bg-primary -left-[6px] top-1.5 border-2 border-zinc-50 dark:border-zinc-950" />
              <div className="flex-1 space-y-1.5">
                <div className="flex justify-between items-start">
                  <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">{item.order}. {item.title}</h4>
                  <span className="text-[10px] bg-zinc-200/60 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-semibold px-2 py-0.5 rounded">
                    🕒 {item.duration_min}m | Owner: {item.owner}
                  </span>
                </div>
                <ul className="list-disc list-inside text-xs text-zinc-600 dark:text-zinc-400 space-y-1 pl-1">
                  {item.talking_points.map((pt, j) => (
                    <li key={j}>{pt}</li>
                  ))}
                </ul>
                <div className="text-[11px] text-violet-600 dark:text-violet-400 italic bg-violet-500/5 p-2 rounded-lg mt-1 border border-violet-500/10">
                  💡 <strong>Strategic Rationale:</strong> {item.why_this_matters}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-zinc-200 dark:border-zinc-800">
        <div className="space-y-2">
          <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">AE Preparation Checklist</div>
          <ul className="space-y-1.5">
            {data.prep_checklist.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-zinc-700 dark:text-zinc-300">
                <input type="checkbox" className="mt-0.5 rounded text-primary focus:ring-primary" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-2">
          <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Suggested Attendees</div>
          <div className="flex flex-wrap gap-1.5">
            {data.suggested_attendees.map((attendee, i) => (
              <span key={i} className="text-xs bg-zinc-200/60 dark:bg-zinc-800 border border-zinc-300/40 dark:border-zinc-800 text-zinc-800 dark:text-zinc-300 px-2.5 py-1 rounded-lg">
                👤 {attendee.name} ({attendee.role})
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 3. Stakeholder Map Card
// ==========================================
interface Stakeholder {
  name: string;
  role: string;
  engagement_level: string;
  sentiment: string;
  days_since_contact: number;
  is_decision_maker: boolean;
  risk_flag: string;
  suggested_action: string;
}

interface StakeholderMapData {
  total_count: number;
  stakeholders: Stakeholder[];
  influence_map: {
    high_influence_champions: string[];
    high_influence_detractors: string[];
    cold_stakeholders: string[];
  };
}

export function StakeholderMapCard({ data }: { data: StakeholderMapData }) {
  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case 'Champion':
        return 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[10px] px-2 py-0.5 rounded-full font-semibold';
      case 'Detractor':
        return 'bg-red-500/10 text-red-500 border border-red-500/20 text-[10px] px-2 py-0.5 rounded-full font-semibold';
      default:
        return 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 text-[10px] px-2 py-0.5 rounded-full font-semibold';
    }
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl p-5 shadow-sm space-y-5">
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="text-xl">👥</span>
          <div>
            <h3 className="font-bold text-zinc-900 dark:text-zinc-50 text-md">Relationship map</h3>
            <p className="text-xs text-zinc-500">Analyzed {data.total_count} active stakeholders in CRM</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl space-y-1">
          <div className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider font-mono">🌟 Champions</div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            {data.influence_map.high_influence_champions.length > 0
              ? data.influence_map.high_influence_champions.join(', ')
              : 'None identified yet'}
          </p>
        </div>
        <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl space-y-1">
          <div className="text-[10px] font-bold text-red-500 uppercase tracking-wider font-mono">⚠️ detractor risks</div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            {data.influence_map.high_influence_detractors.length > 0
              ? data.influence_map.high_influence_detractors.join(', ')
              : 'None flagged'}
          </p>
        </div>
        <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-xl space-y-1">
          <div className="text-[10px] font-bold text-amber-500 uppercase tracking-wider font-mono">❄️ cold contacts</div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">
            {data.influence_map.cold_stakeholders.length > 0
              ? data.influence_map.cold_stakeholders.join(', ')
              : 'All regularly engaged'}
          </p>
        </div>
      </div>

      <div className="space-y-2.5">
        <div className="text-[11px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Stakeholder Directory</div>
        <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {data.stakeholders.map((s, i) => (
            <div key={i} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 first:pt-0 last:pb-0">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">{s.name}</span>
                  {s.is_decision_maker && (
                    <span className="bg-amber-500/10 text-amber-600 text-[9px] font-bold px-1.5 py-0.2 rounded uppercase">DM</span>
                  )}
                  {s.risk_flag === 'COLD_CONTACT' && (
                    <span className="bg-red-500/10 text-red-500 text-[9px] font-bold px-1.5 py-0.2 rounded uppercase animate-pulse">COLD</span>
                  )}
                </div>
                <p className="text-xs text-zinc-500">{s.role} • Engagement: {s.engagement_level}</p>
              </div>

              <div className="flex items-center gap-3 self-end sm:self-auto">
                <span className={getSentimentBadge(s.sentiment)}>{s.sentiment}</span>
                <span className="text-[11px] text-zinc-500">
                  {s.days_since_contact >= 0 ? `💬 ${s.days_since_contact}d ago` : '💬 Never'}
                </span>
                <button className="text-[10px] font-bold text-primary border border-primary/20 bg-primary/5 px-2.5 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-all">
                  {s.suggested_action}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ==========================================
// 4. Risk Review Card
// ==========================================
interface SingleThreadedRisk {
  opp_name: string;
  value_usd: number;
  suggested_action: string;
}

interface StallingDealRisk {
  opp_name: string;
  days_stalled: number;
  stage: string;
}

interface CriticalCaseRisk {
  case_id: string;
  priority: string;
  age_days: number;
}

interface CompetitorThreatRisk {
  opp_name: string;
  competitor: string;
  value_usd: number;
}

interface RiskReviewData {
  revenue_at_risk_usd: number;
  risk_buckets: {
    single_threaded: SingleThreadedRisk[];
    stalling_deals: StallingDealRisk[];
    critical_cases: CriticalCaseRisk[];
    competitor_threat: CompetitorThreatRisk[];
  };
  risk_summary: string;
}

export function RiskReviewCard({ data }: { data: RiskReviewData }) {
  const hasRisks = 
    data.risk_buckets.single_threaded.length > 0 ||
    data.risk_buckets.stalling_deals.length > 0 ||
    data.risk_buckets.critical_cases.length > 0 ||
    data.risk_buckets.competitor_threat.length > 0;

  const formatUSD = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 rounded-2xl p-5 shadow-sm space-y-5">
      <div className="border-b border-zinc-200 dark:border-zinc-800 pb-3 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚠️</span>
          <div>
            <h3 className="font-bold text-zinc-900 dark:text-zinc-50 text-md">Risk Triaging</h3>
            <p className="text-xs text-zinc-500">Pipeline revenue risks assessment</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-bold text-red-500 uppercase tracking-wider font-mono">Revenue at Risk</div>
          <div className="font-bold text-red-500 text-lg leading-none">{formatUSD(data.revenue_at_risk_usd)}</div>
        </div>
      </div>

      <div className="bg-red-500/10 border-l-4 border-l-red-500 p-4 rounded-r-xl text-xs text-red-900 dark:text-red-300 leading-relaxed font-semibold">
        🚨 {data.risk_summary}
      </div>

      {hasRisks ? (
        <div className="space-y-4">
          {data.risk_buckets.single_threaded.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Single-Threaded Deal Vulnerability</div>
              {data.risk_buckets.single_threaded.map((r, i) => (
                <div key={i} className="p-3 bg-zinc-100 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center justify-between text-xs gap-3">
                  <div className="space-y-1">
                    <div className="font-bold text-zinc-900 dark:text-zinc-100">{r.opp_name} ({formatUSD(r.value_usd)})</div>
                    <div className="text-zinc-500">Mitigate: {r.suggested_action}</div>
                  </div>
                  <button className="bg-primary text-primary-foreground font-semibold px-2.5 py-1.5 rounded-lg hover:opacity-90 active:scale-95 transition-all text-[10px]">
                    Find Sponsors
                  </button>
                </div>
              ))}
            </div>
          )}

          {data.risk_buckets.stalling_deals.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Stalled pipeline deals</div>
              {data.risk_buckets.stalling_deals.map((r, i) => (
                <div key={i} className="p-3 bg-zinc-100 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center justify-between text-xs gap-3">
                  <div className="space-y-1">
                    <div className="font-bold text-zinc-900 dark:text-zinc-100">{r.opp_name}</div>
                    <div className="text-zinc-500">Stalled in <span className="font-semibold">{r.stage}</span> stage for {r.days_stalled} days</div>
                  </div>
                  <button className="bg-zinc-800 dark:bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-semibold px-2.5 py-1.5 rounded-lg active:scale-95 transition-all text-[10px]">
                    Create Action Plan
                  </button>
                </div>
              ))}
            </div>
          )}

          {data.risk_buckets.critical_cases.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Critical Support Escalations</div>
              {data.risk_buckets.critical_cases.map((r, i) => (
                <div key={i} className="p-3 bg-zinc-100 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center justify-between text-xs gap-3">
                  <div className="space-y-1">
                    <div className="font-bold text-zinc-900 dark:text-zinc-100">Ticket: {r.case_id} ({r.priority})</div>
                    <div className="text-zinc-500">Unresolved and active for {r.age_days} days</div>
                  </div>
                  <button className="bg-amber-500 text-zinc-950 font-bold px-2.5 py-1.5 rounded-lg hover:opacity-90 active:scale-95 transition-all text-[10px]">
                    Ping Engineering
                  </button>
                </div>
              ))}
            </div>
          )}

          {data.risk_buckets.competitor_threat.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest font-mono">Competitor Intrusion Risk</div>
              {data.risk_buckets.competitor_threat.map((r, i) => (
                <div key={i} className="p-3 bg-zinc-100 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center justify-between text-xs gap-3">
                  <div className="space-y-1">
                    <div className="font-bold text-zinc-900 dark:text-zinc-100">{r.opp_name} ({formatUSD(r.value_usd)})</div>
                    <div className="text-zinc-500">Intrusion type: {r.competitor}</div>
                  </div>
                  <button className="bg-red-500 text-white font-bold px-2.5 py-1.5 rounded-lg hover:opacity-90 active:scale-95 transition-all text-[10px]">
                    Get Battlecard
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-6 text-zinc-500 text-xs">
          ✅ No active vulnerabilities or threats flagged for this account.
        </div>
      )}
    </div>
  );
}
