import os
import json
import datetime
from typing import Dict, Any, Optional
from reasoning_engine import ResponseGenerator
from agent_pipeline import clean_and_parse_json

class ExecEmailHandler:
    @staticmethod
    def handle(account_data: Dict[str, Any], query: str, active_account: Optional[str] = None, is_local: bool = True) -> Dict[str, Any]:
        """Runs a focused prompt to draft an executive email."""
        generator = ResponseGenerator(is_local=is_local)
        
        system_prompt = (
            "You are a professional B2B sales assistant. Write a personalized executive outreach email based on the CRM account data. "
            "Structure your output as a raw JSON object with the following fields:\n"
            "- subject: Clear, professional subject line.\n"
            "- body: Clear, concise, personalized email body using the account details.\n"
            "- suggested_recipients: Array of objects with 'name' and 'role' from the provided contacts.\n"
            "- send_later_hint: A short strategic tip on the best time to send this email.\n\n"
            "CRITICAL: Output ONLY valid JSON. Do not include markdown wraps."
        )
        user_prompt = f"User Request: {query}\nActive Account: {active_account or 'Global'}\nCRM Context:\n{json.dumps(account_data, indent=2)}"
        
        raw_output = ""
        try:
            raw_output = generator._call_llm(system_prompt, user_prompt, timeout=30)
            parsed = clean_and_parse_json(raw_output)
            parsed["type"] = "EXEC_EMAIL"
            if "suggested_recipients" not in parsed:
                contacts = account_data.get("contacts", [])
                parsed["suggested_recipients"] = [{"name": c.get("name"), "role": c.get("role")} for c in contacts[:2]]
            return parsed
        except Exception as e:
            print(f"[QuickActions] ExecEmailHandler error: {e}. Raw: {raw_output}")
            contacts = account_data.get("contacts", [])
            return {
                "type": "EXEC_EMAIL",
                "subject": f"Follow-up regarding {active_account or 'opportunities'}",
                "body": f"Dear team,\n\nI wanted to reach out regarding our active discussions. Please let me know your availability for a short sync.\n\nBest regards,\nAccount Manager",
                "suggested_recipients": [{"name": c.get("name"), "role": c.get("role")} for c in contacts[:2]],
                "send_later_hint": "Send manually during business hours."
            }

class MeetingAgendaHandler:
    @staticmethod
    def handle(account_data: Dict[str, Any], query: str, active_account: Optional[str] = None, is_local: bool = True) -> Dict[str, Any]:
        """Runs a focused prompt to generate a structured, timed meeting agenda."""
        generator = ResponseGenerator(is_local=is_local)
        
        system_prompt = (
            "You are a sales assistant. Create a timed meeting agenda based on the CRM account data. "
            "Structure your output as a raw JSON object with the following fields:\n"
            "- meeting_title: Title of the meeting.\n"
            "- audience_type: Pick 'Executive', 'Technical', or 'Commercial'.\n"
            "- duration_minutes: Total meeting duration in minutes.\n"
            "- agenda_items: Array of timed agenda segments. Each segment has 'order', 'title', 'duration_min', 'owner' (e.g. AE, Client), 'talking_points' (array of strings), and 'why_this_matters' (reasoning based on CRM facts).\n"
            "- prep_checklist: List of actions the team should take to prepare for this meeting.\n"
            "- suggested_attendees: Array of contact names and roles from the CRM context.\n\n"
            "CRITICAL: Output ONLY valid JSON. Do not include markdown wraps."
        )
        user_prompt = f"User Request: {query}\nActive Account: {active_account or 'Global'}\nCRM Context:\n{json.dumps(account_data, indent=2)}"
        
        raw_output = ""
        try:
            raw_output = generator._call_llm(system_prompt, user_prompt, timeout=30)
            parsed = clean_and_parse_json(raw_output)
            parsed["type"] = "MEETING_AGENDA"
            return parsed
        except Exception as e:
            print(f"[QuickActions] MeetingAgendaHandler error: {e}. Raw: {raw_output}")
            contacts = account_data.get("contacts", [])
            return {
                "type": "MEETING_AGENDA",
                "meeting_title": f"Alignment Meeting with {active_account or 'Client'}",
                "audience_type": "Executive",
                "duration_minutes": 30,
                "agenda_items": [
                    {
                        "order": 1,
                        "title": "Welcome and Objectives",
                        "duration_min": 10,
                        "owner": "AE",
                        "talking_points": ["Align on project goals", "Review current timelines"],
                        "why_this_matters": "Establish meeting focus."
                    },
                    {
                        "order": 2,
                        "title": "Open Discussion & Next Steps",
                        "duration_min": 20,
                        "owner": "All",
                        "talking_points": ["Address blockers", "Confirm action items"],
                        "why_this_matters": "Drive deal progression."
                    }
                ],
                "prep_checklist": ["Review recent support cases", "Prepare pricing slide"],
                "suggested_attendees": [{"name": c.get("name"), "role": c.get("role")} for c in contacts[:2]]
            }

class StakeholderHandler:
    @staticmethod
    def handle(account_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Deterministic mapping of contacts to sentiment, influence, and risk flags."""
        contacts = account_data.get("contacts", [])
        stakeholders = []
        high_influence_champions = []
        high_influence_detractors = []
        cold_stakeholders = []
        
        current_date = datetime.date(2026, 7, 14)
        
        for c in contacts:
            name = c.get("name", "Unknown Contact")
            role = c.get("role", "Stakeholder")
            eng_level = c.get("engagement_level", "Medium")
            
            sentiment = "Neutral"
            if eng_level == "High":
                sentiment = "Champion"
            elif eng_level == "Low":
                sentiment = "Detractor"
                
            last_contact_str = c.get("last_contact_date", "Never")
            days_since = 999
            risk_flag = "NONE"
            
            if last_contact_str and last_contact_str != "Never":
                try:
                    parts = [int(x) for x in last_contact_str.split("-") if x.isdigit()]
                    if len(parts) == 3:
                        dt = datetime.date(parts[0], parts[1], parts[2])
                        days_since = (current_date - dt).days
                except Exception:
                    pass
            
            if days_since > 30:
                risk_flag = "COLD_CONTACT"
                
            is_dm = any(kw in role.lower() for kw in ["director", "vp", "cxo", "chief", "head", "manager", "lead"]) or eng_level == "High"
            
            if risk_flag == "COLD_CONTACT":
                action = f"Draft re-engagement email to {name}"
            elif sentiment == "Detractor":
                action = f"Schedule 1-on-1 alignment session to address concerns"
            else:
                action = f"Send standard pipeline update or follow up"
                
            stakeholder_info = {
                "name": name,
                "role": role,
                "engagement_level": eng_level,
                "sentiment": sentiment,
                "days_since_contact": days_since if days_since != 999 else -1,
                "is_decision_maker": is_dm,
                "risk_flag": risk_flag,
                "suggested_action": action
            }
            stakeholders.append(stakeholder_info)
            
            if is_dm:
                if sentiment == "Champion":
                    high_influence_champions.append(name)
                elif sentiment == "Detractor":
                    high_influence_detractors.append(name)
            if risk_flag == "COLD_CONTACT":
                cold_stakeholders.append(name)
                
        return {
            "type": "STAKEHOLDERS",
            "total_count": len(stakeholders),
            "stakeholders": stakeholders,
            "influence_map": {
                "high_influence_champions": high_influence_champions,
                "high_influence_detractors": high_influence_detractors,
                "cold_stakeholders": cold_stakeholders
            }
        }

class RiskReviewHandler:
    @staticmethod
    def handle(account_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Deterministic grouping of open threats, stalling opportunities, and P1 support cases."""
        opportunities = account_data.get("opportunities", [])
        contacts = account_data.get("contacts", [])
        cases = account_data.get("cases", [])
        
        single_threaded_list = []
        stalling_deals_list = []
        critical_cases_list = []
        competitor_threat_list = []
        total_rev_at_risk = 0.0
        
        dm_count = sum(1 for c in contacts if any(kw in c.get("role", "").lower() for kw in ["director", "vp", "cxo", "chief", "head"]))
        is_single_threaded = len(contacts) <= 2 or dm_count == 0
        
        if is_single_threaded and opportunities:
            for o in opportunities:
                val = o.get("amount_usd", 0.0)
                single_threaded_list.append({
                    "opp_name": o.get("opp_name", "Unknown Opportunity"),
                    "value_usd": val,
                    "suggested_action": "Identify & engage at least two additional department sponsors."
                })
                total_rev_at_risk += val
                
        for o in opportunities:
            stage = o.get("stage", "")
            val = o.get("amount_usd", 0.0)
            if any(kw in stage.lower() for kw in ["negotiation", "proposal", "commercial"]):
                stalling_deals_list.append({
                    "opp_name": o.get("opp_name", ""),
                    "days_stalled": 45,
                    "stage": stage
                })
                if not is_single_threaded:
                    total_rev_at_risk += val
                    
        for c in cases:
            priority = c.get("priority", "Medium")
            status = c.get("status", "Closed")
            if priority in ["High", "P1", "Critical"] and status != "Closed":
                critical_cases_list.append({
                    "case_id": c.get("case_id", "Unknown"),
                    "priority": priority,
                    "age_days": 10
                })
                
        health_score = account_data.get("health_score", 100.0)
        if health_score < 50.0 and opportunities:
            for o in opportunities:
                val = o.get("amount_usd", 0.0)
                competitor_threat_list.append({
                    "opp_name": o.get("opp_name", ""),
                    "competitor": "Competitor replacement threat",
                    "value_usd": val
                })
                
        summary_lines = []
        if single_threaded_list:
            summary_lines.append(f"Account is single-threaded ({len(contacts)} contacts).")
        if stalling_deals_list:
            summary_lines.append(f"{len(stalling_deals_list)} active deals showing stagnation.")
        if critical_cases_list:
            summary_lines.append(f"There are {len(critical_cases_list)} unresolved critical customer service cases.")
        if competitor_threat_list:
            summary_lines.append("Low client health indicators suggest active competitor replacement risk.")
            
        if not summary_lines:
            risk_summary = "Account health parameters are nominal. No critical risks detected."
        else:
            risk_summary = " ".join(summary_lines)
            
        return {
            "type": "RISK_REVIEW",
            "revenue_at_risk_usd": total_rev_at_risk,
            "risk_buckets": {
                "single_threaded": single_threaded_list,
                "stalling_deals": stalling_deals_list,
                "critical_cases": critical_cases_list,
                "competitor_threat": competitor_threat_list
            },
            "risk_summary": risk_summary
        }

def dispatch_quick_action(action_type: str, account_data: Dict[str, Any], query: str, active_account: Optional[str] = None, is_local: bool = True) -> Dict[str, Any]:
    """Universal dispatcher for the 4 core quick-actions."""
    if action_type == "EXEC_EMAIL" or action_type == "DRAFT_EMAIL":
        return ExecEmailHandler.handle(account_data, query, active_account, is_local)
    elif action_type == "MEETING_AGENDA":
        return MeetingAgendaHandler.handle(account_data, query, active_account, is_local)
    elif action_type == "SHOW_STAKEHOLDERS":
        return StakeholderHandler.handle(account_data, query)
    elif action_type == "REVIEW_RISKS":
        return RiskReviewHandler.handle(account_data, query)
    else:
        raise ValueError(f"Unknown action type: {action_type}")
