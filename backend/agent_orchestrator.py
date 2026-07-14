import os
import sys
import json
import pandas as pd
from typing import List, Dict, Any, Optional

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engine import DataEngine
from intent_classifier import IntentClassifier, IntentClassificationOutput
from reasoning_engine import (
    ReasoningEngine, ResponseGenerator, ConsensusOutput
)

class DataQualityResult:
    def __init__(self, overall_sufficiency: float, limiting_factors: List[str] = None):
        self.overall_sufficiency = overall_sufficiency
        self.limiting_factors = limiting_factors or []

class DataRetrieval:
    def __init__(self, engine: DataEngine):
        self.engine = engine

    def fetch(self, intent: IntentClassificationOutput) -> Dict[str, Any]:
        """
        Fetch account-specific context from the CRM database matching target account name.
        """
        accounts_df = self.engine.data.get('account')
        if accounts_df is None or accounts_df.empty:
            return {
                "account_id": None,
                "account_name": "No accounts loaded",
                "health_score": 50,
                "opportunities": [],
                "contacts": [],
                "activities": [],
                "cases": []
            }
            
        acc_name = intent.extracted_entities.account
        acc_row = pd.DataFrame()
        
        if acc_name:
            # Case-insensitive substring match on Account_Name or Account_ID
            matching = accounts_df[
                accounts_df['Account_Name'].str.lower().str.contains(acc_name.lower(), na=False) |
                accounts_df['Account_ID'].str.lower().str.contains(acc_name.lower(), na=False)
            ]
            if not matching.empty:
                acc_row = matching.iloc[0]
                
        if acc_row.empty:
            acc_id = None
            acc_name = acc_name or "Global Portfolio View"
            health_score = self.engine.calculate_portfolio_health_score()
        else:
            acc_id = str(acc_row.get('Account_ID', ''))
            acc_name = str(acc_row.get('Account_Name', ''))
            health_score = float(acc_row.get('Health_Score', 80.0))
            
        # Opportunities
        opps_df = self.engine.data.get('opportunity')
        opps_list = []
        if opps_df is not None and not opps_df.empty:
            matching_opps = opps_df
            if acc_id:
                matching_opps = matching_opps[matching_opps['Account_ID'] == acc_id]
            
            target_stage = intent.extracted_entities.stage
            if target_stage:
                matching_opps = matching_opps[matching_opps['Stage'].str.lower().str.contains(target_stage.lower(), na=False)]
                
            for _, r in matching_opps.iterrows():
                opps_list.append({
                    "opp_id": str(r.get('Opp_ID', '')),
                    "opp_name": str(r.get('Opp_Name', '')),
                    "amount_usd": float(r.get('Amount_USD', 0.0)),
                    "stage": str(r.get('Stage', '')),
                    "close_date": str(r.get('Close_Date', ''))
                })
                
        # Contacts
        contacts_df = self.engine.data.get('contact')
        contacts_list = []
        if contacts_df is not None and not contacts_df.empty and acc_id:
            matching_contacts = contacts_df[contacts_df['Account_ID'] == acc_id]
            for _, r in matching_contacts.iterrows():
                contacts_list.append({
                    "contact_id": str(r.get('Contact_ID', '')),
                    "name": f"{r.get('First_Name', '')} {r.get('Last_Name', '')}".strip(),
                    "role": str(r.get('Role', '')),
                    "engagement_level": str(r.get('Engagement_Level', '')),
                    "last_contact_date": str(r.get('Last_Contact_Date', ''))[:10] if pd.notna(r.get('Last_Contact_Date')) else "Never"
                })
                
        # Cases
        cases_df = self.engine.data.get('case')
        cases_list = []
        if cases_df is not None and not cases_df.empty and acc_id:
            matching_cases = cases_df[cases_df['Account_ID'] == acc_id]
            for _, r in matching_cases.iterrows():
                cases_list.append({
                    "case_id": str(r.get('Case_ID', '')),
                    "subject": str(r.get('Subject', '')),
                    "severity": str(r.get('Severity', '')),
                    "status": str(r.get('Status', ''))
                })

        # Activities
        activities_df = self.engine.data.get('activity')
        activities_list = []
        if activities_df is not None and not activities_df.empty and acc_id:
            matching_activities = activities_df[activities_df['Account_ID'] == acc_id]
            for _, r in matching_activities.iterrows():
                activities_list.append({
                    "activity_id": str(r.get('Activity_ID', '')),
                    "type": str(r.get('Type', '')),
                    "description": str(r.get('Description', '')),
                    "date": str(r.get('Activity_Date', ''))
                })
                
        pipeline_breakdown = {}
        if opps_list:
            pipeline_breakdown = {
                "total_usd": sum(o.get("amount_usd", 0.0) for o in opps_list),
                "breakdown": [
                    f"{o['opp_name']}: ${o['amount_usd']:,.0f}" for o in opps_list
                ]
            }

        return {
            "account_id": acc_id,
            "account_name": acc_name,
            "health_score": health_score,
            "opportunities": opps_list,
            "contacts": contacts_list,
            "activities": activities_list,
            "cases": cases_list,
            "pipeline_breakdown": pipeline_breakdown
        }

    def get_market_context(self) -> Dict[str, Any]:
        """
        Fetch strategic market details.
        """
        return {
            "competitive_threats": [
                "Competitor A pitch observed on multiple enterprise accounts",
                "Competitor B discounting prices by 25%"
            ],
            "peer_accounts": [
                {"account": "Wipro", "health_score": 0.65},
                {"account": "TCS", "health_score": 0.80}
            ],
            "company_okrs": [
                "Increase retention in enterprise accounts to >95%",
                "Expand ARR in APAC by 20%"
            ],
            "competitive_context": "Competitor A is actively pitching a replacement solution."
        }

    def assess_quality(self, account_data: Dict[str, Any]) -> float:
        """
        Calculate target account CRM data sufficiency (0.0 to 1.0).
        """
        acc_id = account_data.get("account_id")
        if not acc_id:
            return 1.0  # Safe default if no specific account was mapped
            
        res = self.engine.calculate_data_sufficiency(acc_id)
        return float(res.get("score", 100)) / 100.0

    def expand_scope(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich account context with global statistics when data quality is low.
        """
        enriched = account_data.copy()
        enriched["expanded_scope_active"] = True
        enriched["portfolio_averages"] = {
            "average_health_score": 78.5,
            "average_deal_size_usd": 125000,
            "average_case_resolution_days": 4.2
        }
        return enriched

    def fetch_with_quality_check(self, intent: IntentClassificationOutput) -> tuple:
        """
        Fetches account data and assesses its quality.
        """
        data = self.fetch(intent)
        acc_id = data.get("account_id")
        if acc_id:
            res = self.engine.calculate_data_sufficiency(acc_id)
            score = float(res.get("score", 100)) / 100.0
            gaps = res.get("reasons", [])
        else:
            score = 1.0
            gaps = []
        return data, DataQualityResult(overall_sufficiency=score, limiting_factors=gaps)

class AccountPlanningAgent:
    def __init__(self, data_engine: Optional[DataEngine] = None, is_local: bool = True):
        self.is_local = is_local
        
        # Resolve data engine exactly like main.py
        if data_engine is None:
            # We import dynamic resolver if needed
            from main import engine as default_engine
            self.data_engine = default_engine
        else:
            self.data_engine = data_engine

        known_accounts = []
        if self.data_engine and self.data_engine.data:
            accounts_df = self.data_engine.data.get('account')
            if accounts_df is not None and not accounts_df.empty and 'Account_Name' in accounts_df.columns:
                known_accounts = accounts_df['Account_Name'].dropna().unique().tolist()
        
        self.intent_classifier = IntentClassifier(known_accounts=known_accounts, is_local=is_local)
            
        self.data_retrieval = DataRetrieval(self.data_engine)
        self.reasoning_engine = ReasoningEngine(is_local=is_local)
        self.response_generator = ResponseGenerator(is_local=is_local)
    
    def process_query(
        self,
        query: str,
        user_role: str,
        recipient_roles: List[str] = ["am"],
        history: Optional[List[Dict[str, str]]] = None,
        active_account: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        End-to-end account planning query processing.
        """
        # LAYER 1: Intent Classification
        from observability import TraceSpanContext
        
        if action_type:
            from intent_classifier import IntentClassificationOutput, ExtractedEntities, IntentEnum
            
            enum_map = {
                "EXEC_EMAIL": IntentEnum.DRAFT_EMAIL,
                "DRAFT_EMAIL": IntentEnum.DRAFT_EMAIL,
                "MEETING_AGENDA": IntentEnum.MEETING_AGENDA,
                "SHOW_STAKEHOLDERS": IntentEnum.SHOW_STAKEHOLDERS,
                "REVIEW_RISKS": IntentEnum.REVIEW_RISKS
            }
            
            intent = IntentClassificationOutput(
                primary_intent=enum_map.get(action_type, IntentEnum.ACTION_RECOMMENDATION),
                confidence_primary=1.0,
                extracted_entities=ExtractedEntities(account=active_account),
                urgency="medium",
                scope="ENTITY",
                intent=action_type,
                complexity="FACTUAL" if action_type in ["SHOW_STAKEHOLDERS", "REVIEW_RISKS"] else "TACTICAL",
                target_entities=[active_account] if active_account else []
            )
            print(f"[Orchestrator] Bypassing intent classifier for action_type: {action_type}")
        else:
            print("[Layer 1] Classifying intent...")
            with TraceSpanContext("PLANNER"):
                intent = self.intent_classifier.classify(query, history, user_role, active_account)
        try:
            intent_data = intent.model_dump()
        except AttributeError:
            intent_data = intent.dict()
        print(f"[Layer 1] Classified Intent Output: {intent_data}")
        
        # Fast path for conversational greetings
        if intent.complexity == "CONVERSATIONAL":
            print("[Governance] CONVERSATIONAL complexity detected: Bypassing normal layers for greeting.")
            import httpx
            
            system_prompt = (
                "You are the APEX Account Planning AI Assistant — an expert strictly focused on "
                "sales account planning, deal pipelines, stakeholder maps, opportunity reviews, "
                "and customer support case management. "
                "Rules you must never break: "
                "1. If the user greets you, welcome them warmly and ask how you can help them "
                "analyze accounts, pipelines, or deals today. "
                "2. If the user says anything unrelated to account planning (jokes, general knowledge, "
                "sports, weather, personal questions), politely decline to answer it and gently "
                "guide them back to an account planning task. "
                "3. Never break character. Never answer off-topic questions. "
                "Keep all responses under 60 words. Be warm, professional, and helpful."
            )
            user_prompt = f"The user says: '{query}'. Respond to them naturally."
            
            welcome_text = ""
            try:
                payload = {
                    "model": self.response_generator.model,
                    "prompt": f"System: {system_prompt}\n\nUser Prompt: {user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 150
                    }
                }
                httpx_timeout = httpx.Timeout(15.0, connect=5.0)
                print(f"  [LLM CONNECT] Attempting greeting connection to: {self.response_generator.url}")
                with httpx.Client(timeout=httpx_timeout) as client:
                    print(f"  [LLM REQUEST] Sending greeting query payload to: {self.response_generator.url}...")
                    response = client.post(self.response_generator.url, json=payload)
                    print(f"  [LLM RESPONSE] Received greeting status {response.status_code} from: {self.response_generator.url}")
                    if response.status_code == 200:
                        welcome_text = response.json().get("response", "").strip()
            except Exception as e:
                print(f"[Warning] LLM call failed for conversational greeting: {e}")
                
            if not welcome_text:
                welcome_text = "Hello! I am your Account Planning expert. How can I help you with your accounts or pipelines today?"
            
            consensus = self.reasoning_engine.run_reasoning_threads(
                account_data={},
                market_context={},
                complexity="CONVERSATIONAL"
            )
            
            responses = {role: {"narrative": welcome_text, "why_this_matters": "Conversational greeting."} for role in recipient_roles}
            
            return {
                "status": "SUCCESS",
                "intent": intent,
                "consensus": consensus,
                "responses": responses,
                "data_quality_score": 100.0,
                "confidence": 1.0,
                "raw_reasoning_bucket": {},
                "raw_response_bucket": {},
                "account_data": {}
            }
        
        # Intent Gatekeeper: Reject low confidence
        if intent.confidence_primary < 0.5:
            # SKIP Layer 2 & 3 if intent is weak
            # Return data-only response (Phase 2 output)
            print("[SYS_LOG] Intent confidence too low. Skipping reasoning threads.")
            data, data_quality = self.data_retrieval.fetch_with_quality_check(intent)
            
            # # OLD LOW_CONFIDENCE PATH (Commented down)
            # return {
            #     "status": "LOW_CONFIDENCE",
            #     "message": f"Could not confidently classify query. Got: {intent.primary_intent} (confidence: {intent.confidence_primary})",
            #     "secondary_options": intent.secondary_intents
            # }
            
            return {
                "status": "INTENT_LOW_CONFIDENCE",
                "intent": intent,
                "data": data,
                "data_quality": data_quality,
                "skip_reasoning": True,
                "confidence": data_quality.overall_sufficiency
            }
        
        # LAYER 2: Data Retrieval
        print("[Layer 2] Retrieving data...")
        with TraceSpanContext("RETRIEVER"):
            account_data, data_quality = self.data_retrieval.fetch_with_quality_check(intent)
            
            # Local RAG Semantic Retrieval
            try:
                from vector_store import vector_store
                acc_id = account_data.get("account_id")
                semantic_matches = vector_store.search_activities(query, user_id=self.data_engine.user_id, account_id=acc_id, limit=3)
                if semantic_matches:
                    account_data["semantic_activities"] = [m["text"] for m in semantic_matches]
                    print(f"[RAG] Appended {len(semantic_matches)} semantically relevant activities to context.")
            except Exception as rag_err:
                print(f"⚠️ Warning: Local RAG semantic search failed: {rag_err}")
        
        # Enabled reasoning on local (run sequential threads)
        # if self.is_local:
        #     # Return data-only response (fast path)
        #     print("[SYS_LOG] Running in local mode. Skipping reasoning threads.")
        #     return {
        #         "status": "DATA_ONLY_LOCAL",
        #         "intent": intent,
        #         "data": account_data,
        #         "data_quality": data_quality,
        #         "skip_reasoning": True,
        #         "confidence": data_quality.overall_sufficiency
        #     }
            
        market_context = self.data_retrieval.get_market_context()
        
        data_quality_val = data_quality.overall_sufficiency
        data_quality_pct = data_quality_val * 100.0
        
        print(f"[Layer 2 Input] Retrieved Account Data: {account_data}")
        print(f"[Layer 2 Input] Market Context: {market_context}")
        print(f"[Layer 2 Input] Data Quality Sufficiency: {data_quality_pct}% (limiting factors: {data_quality.limiting_factors})")

        if data_quality_val < 0.4:
            print(f"[WARNING] Critical low data quality: {data_quality_val}. Expanding scope...")
            account_data = self.data_retrieval.expand_scope(account_data)
            print(f"[Layer 2 Input - Expanded Scope] Updated Account Data: {account_data}")
        
        # Fast path for explicit quick-action tasks
        QUICK_ACTION_INTENTS = {"DRAFT_EMAIL", "EXEC_EMAIL", "MEETING_AGENDA", "SHOW_STAKEHOLDERS", "REVIEW_RISKS"}
        if intent.intent in QUICK_ACTION_INTENTS:
            print(f"[Governance] {intent.intent} detected: Running targeted quick-action dispatch.")
            import json
            from quick_actions_handler import dispatch_quick_action
            
            action_result = dispatch_quick_action(
                action_type=intent.intent,
                account_data=account_data,
                query=query,
                active_account=active_account,
                is_local=self.is_local
            )
            
            serialized_narrative = json.dumps(action_result)
            
            intent.complexity = "FACTUAL"
            consensus = self.reasoning_engine.run_reasoning_threads(
                account_data=account_data,
                market_context={},
                complexity="FACTUAL"
            )
            
            responses = {role: {"narrative": serialized_narrative, "why_this_matters": f"Quick action {intent.intent} executed."} for role in recipient_roles}
            
            return {
                "status": "SUCCESS",
                "intent": intent,
                "consensus": consensus,
                "responses": responses,
                "data_quality_score": data_quality_pct,
                "confidence": 1.0,
                "raw_reasoning_bucket": {},
                "raw_response_bucket": {},
                "account_data": account_data
            }

        # Check if FACTUAL complexity
        if intent.complexity == "FACTUAL":
            print("[Governance] Resolving FACTUAL query directly in Python.")
            factual_answer = ""
            if intent.intent == "CONTACT_LOOKUP":
                contacts = account_data.get("contacts", [])
                if contacts:
                    contact_lines = []
                    for c in contacts[:5]:
                        contact_lines.append(f"• {c.get('name')} - {c.get('role')} (Engagement: {c.get('engagement_level')}, Last Contacted: {c.get('last_contact_date')})")
                    factual_answer = f"The following contacts were found for {account_data.get('account_name')}:\n" + "\n".join(contact_lines)
                else:
                    factual_answer = f"No contacts found for {account_data.get('account_name')} in the database."
            elif intent.intent == "OPPORTUNITY_RANKING":
                opps = account_data.get("opportunities", [])
                if opps:
                    opp_lines = []
                    for i, o in enumerate(opps[:5]):
                        opp_lines.append(f"{i+1}. {o.get('opp_name')} - ${o.get('amount_usd'):,.2f} ({o.get('stage')})")
                    factual_answer = f"Top opportunities for {account_data.get('account_name')}:\n" + "\n".join(opp_lines)
                else:
                    factual_answer = f"No opportunities found for {account_data.get('account_name')}."
            else:
                factual_answer = f"Grounded data summary for {account_data.get('account_name')}: {len(account_data.get('opportunities', []))} active opportunities, {len(account_data.get('contacts', []))} contacts mapped."

            # Bypass Layer 2 LLM and Layer 3 LLM
            consensus = self.reasoning_engine.run_reasoning_threads(
                account_data=account_data,
                market_context={},
                complexity="FACTUAL"
            )
            responses = {}
            for role in recipient_roles:
                responses[role] = {"narrative": factual_answer, "why_this_matters": "Factual query completed."}
            
            return {
                "status": "SUCCESS",
                "intent": intent,
                "consensus": consensus,
                "responses": responses,
                "data_quality_score": data_quality_pct,
                "confidence": 1.0,
                "raw_reasoning_bucket": {},
                "raw_response_bucket": {},
                "account_data": account_data
            }

        # LAYER 2: Reasoning (Multi-perspective)
        print("[Layer 2] Running reasoning threads...")
        
        # Extract requested opportunity count if specified
        requested_count = 5
        metric_str = ""
        try:
            if hasattr(intent, "extracted_entities") and intent.extracted_entities:
                metric_str = intent.extracted_entities.get("metric") or ""
        except Exception:
            pass
        
        import re
        digits = re.findall(r"\b\d+\b", f"{metric_str} {query}")
        if digits:
            try:
                parsed_num = int(digits[0])
                if 1 <= parsed_num <= 10:
                    requested_count = parsed_num
            except Exception:
                pass
        
        with TraceSpanContext("REASONER"):
            consensus = self.reasoning_engine.run_reasoning_threads(
                account_data=account_data,
                market_context=market_context,
                timeout_per_thread=45,
                total_timeout=90,
                local=self.is_local,
                complexity=intent.complexity,
                requested_count=requested_count,
                history=history
            )
        
        # Cap reasoning confidence scores based on data sufficiency
        if data_quality_val < 0.4:
            consensus.final_confidence = min(consensus.final_confidence, 0.5)
            consensus.agreement_score = min(consensus.agreement_score, 0.5)
            consensus.confidence_limiting_factors.append(
                f"Data sufficiency is extremely low ({data_quality_pct:.1f}%). Capping confidence at 50%."
            )
        elif data_quality_val < 0.7:
            consensus.final_confidence = min(consensus.final_confidence, 0.8)
            consensus.confidence_limiting_factors.append(
                f"Data sufficiency is moderate ({data_quality_pct:.1f}%). Capping confidence at 80%."
            )
        
        try:
            consensus_data = consensus.model_dump()
        except AttributeError:
            consensus_data = consensus.dict()
        print(f"[Layer 2 Output] Consensus Synthesis: {consensus_data}")
        
        # LAYER 3: Response Generation (Role-specific)
        print("[Layer 3] Generating responses...")
        responses = {}
        with TraceSpanContext("NARRATOR"):
            for role in recipient_roles:
                print(f"[Layer 3 Input] Generating response for role: {role.upper()}")
                responses[role] = self.response_generator.generate_response(
                    consensus,
                    recipient_role=role
                )
                try:
                    resp_data = responses[role].model_dump()
                except AttributeError:
                    resp_data = responses[role].dict()
                print(f"[Layer 3 Output] Response for {role.upper()}: {resp_data}")
        
        # Print raw LLM output buckets for under-the-hood debugging
        print(f"[Layer 2 Raw LLM Output Bucket] {self.reasoning_engine.raw_reasoning_bucket}")
        print(f"[Layer 3 Raw LLM Output Bucket] {self.response_generator.raw_response_bucket}")
        
        return {
            "status": "SUCCESS",
            "intent": intent,
            "consensus": consensus,
            "responses": responses,
            "data_quality_score": data_quality_pct,
            "confidence": consensus.final_confidence,
            "raw_reasoning_bucket": self.reasoning_engine.raw_reasoning_bucket,
            "raw_response_bucket": self.response_generator.raw_response_bucket,
            "account_data": account_data
        }

    def _get_market_context(self):
        """Get market/competitive context for reasoning."""
        base_context = self.data_retrieval.get_market_context()
        return {
            "market_threats": base_context.get("competitive_threats", []),
            "company_okrs": base_context.get("company_okrs", []),
            "competitive_landscape": {"context": base_context.get("competitive_context", "")}
        }

    def _build_consensus_from_threads(self, threads):
        """Build consensus from reasoning thread results (fallback/utility helper)."""
        final_conf = sum([
            threads.get('am', {}).get('confidence', 0.5),
            threads.get('vp', {}).get('confidence', 0.5),
            threads.get('svp', {}).get('confidence', 0.5),
            threads.get('data', {}).get('confidence', 0.5)
        ]) / 4
        
        return ConsensusOutput(
            consensus_recommendation={"action": threads.get('am', {}).get('playbook_7day', [])},
            thread_agreement={
                "am": threads.get('am', {}).get('confidence', 0.5),
                "vp": threads.get('vp', {}).get('confidence', 0.5),
                "svp": threads.get('svp', {}).get('confidence', 0.5),
                "data": threads.get('data', {}).get('confidence', 0.5)
            },
            agreement_score=0.75,
            dissenting_views=[],
            confidence_limiting_factors=[],
            final_confidence=final_conf
        )

