"""
PIPELINE LOGGER & TOKEN ACCUMULATOR (pipeline_logger.py)
Provides boxed console/file logging, thread-local token tracking,
and writes structured evaluation records to JSONL log files.
"""

# --- SECTION 1: Dependencies & Model Pricing Rates ---
# Defines token cost constants for Gemini 2.5 Flash pricing calculations.
import os
import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("pipeline")

GEMINI_FLASH_INPUT_COST_PER_1M = 0.075
GEMINI_FLASH_OUTPUT_COST_PER_1M = 0.30

# --- SECTION 2: Thread-Local Token Accumulator ---
# Tracks prompt tokens, completion tokens, call durations, and costs across thread pools.
class TokenAccumulator:
    _thread_local = threading.local()

    @classmethod
    def _get_storage(cls) -> Dict[str, Any]:
        if not hasattr(cls._thread_local, "data"):
            cls._thread_local.data = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "calls": []
            }
        return cls._thread_local.data

    @classmethod
    def reset(cls):
        cls._thread_local.data = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "calls": []
        }

    @classmethod
    def record_call(cls, call_name: str, prompt_tokens: int, completion_tokens: int, duration_ms: int = 0):
        storage = cls._get_storage()
        storage["prompt_tokens"] += prompt_tokens
        storage["completion_tokens"] += completion_tokens
        
        input_cost = (prompt_tokens / 1_000_000.0) * GEMINI_FLASH_INPUT_COST_PER_1M
        output_cost = (completion_tokens / 1_000_000.0) * GEMINI_FLASH_OUTPUT_COST_PER_1M
        call_cost = input_cost + output_cost

        storage["calls"].append({
            "call_name": call_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(call_cost, 6),
            "duration_ms": duration_ms
        })

    @classmethod
    def snapshot(cls) -> Dict[str, Any]:
        storage = cls._get_storage()
        p_tokens = storage["prompt_tokens"]
        c_tokens = storage["completion_tokens"]
        t_tokens = p_tokens + c_tokens
        
        input_cost = (p_tokens / 1_000_000.0) * GEMINI_FLASH_INPUT_COST_PER_1M
        output_cost = (c_tokens / 1_000_000.0) * GEMINI_FLASH_OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost

        return {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": t_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "total_llm_calls": len(storage["calls"]),
            "calls": storage["calls"]
        }


class PipelineLogger:
    @staticmethod
    def start(query: str, session_id: str, user_role: str = "am", trace_id: str = ""):
        try:
            TokenAccumulator.reset()
            border = "=" * 66
            q_str = str(query or "")
            s_id = str(session_id or "")[:12]
            t_id = str(trace_id or "")[:12]
            logger.info(f"\n+{border}+\n|  APEX PIPELINE START  |  Trace: {t_id}  |  Session: {s_id}  |\n+{border}+")
            logger.info(f"  [INPUT] Query: \"{q_str}\" | Role: {user_role}")
        except Exception as err:
            logger.warning(f"[PipelineLogger] start error: {err}")

    @staticmethod
    def layer1(intent_name: str, confidence: float, complexity: str, scope: str = "ENTITY", duration_ms: int = 0):
        try:
            conf_val = float(confidence) if confidence is not None else 1.0
            conf_str = "HIGH" if conf_val >= 0.8 else ("MEDIUM" if conf_val >= 0.5 else "LOW")
            iname = str(intent_name or "ACTION_RECOMMENDATION")
            cmplx = str(complexity or "TACTICAL")
            scp = str(scope or "ENTITY")
            logger.info(f"+- L1 INTENT CLASSIFICATION ───────────────────────────── [{duration_ms}ms] -+")
            logger.info(f"|  Intent    : {iname:<30} Scope: {scp:<10} |")
            logger.info(f"|  Complexity: {cmplx:<30} Conf : {conf_val:.2f} ({conf_str}) |")
            logger.info(f"+-----------------------------------------------------------------+")
        except Exception as err:
            logger.warning(f"[PipelineLogger] layer1 error: {err}")

    @staticmethod
    def layer2(account_name: str, data_summary: Dict[str, Any], data_quality_pct: float, rag_hits: int = 0, duration_ms: int = 0):
        try:
            acc_name = str(account_name or "Global")
            opps_cnt = data_summary.get("opps_count", 0) if isinstance(data_summary, dict) else 0
            contacts_cnt = data_summary.get("contacts_count", 0) if isinstance(data_summary, dict) else 0
            cases_cnt = data_summary.get("cases_count", 0) if isinstance(data_summary, dict) else 0
            total_rev = float(data_summary.get("total_pipeline_usd", 0.0) or 0.0) if isinstance(data_summary, dict) else 0.0
            stalled_val = float(data_summary.get("stalled_usd", 0.0) or 0.0) if isinstance(data_summary, dict) else 0.0
            health = float(data_summary.get("health_score", 80.0) or 80.0) if isinstance(data_summary, dict) else 80.0
            dq_pct = float(data_quality_pct or 100.0)

            logger.info(f"+- L2 DATA RETRIEVAL ────────────────────────────────────── [{duration_ms}ms] -+")
            logger.info(f"|  Account   : {acc_name:<50} |")
            logger.info(f"|  CRM Data  : Opps: {opps_cnt} | Contacts: {contacts_cnt} | Cases: {cases_cnt} | RAG Hits: {rag_hits:<6} |")
            logger.info(f"|  Pipeline  : ${total_rev:,.0f} | Stalled: ${stalled_val:,.0f} | Health: {health:.1f}/100    |")
            logger.info(f"|  Data Qual : {dq_pct:.1f}%                                               |")
            logger.info(f"+-----------------------------------------------------------------+")
        except Exception as err:
            logger.warning(f"[PipelineLogger] layer2 error: {err}")

    @staticmethod
    def llm_call(stage_name: str, prompt_tokens: int, completion_tokens: int, duration_ms: int = 0):
        try:
            TokenAccumulator.record_call(stage_name, prompt_tokens, completion_tokens, duration_ms)
            tot = prompt_tokens + completion_tokens
            logger.info(f"  [L3 LLM] {stage_name:<24} | Tokens: {prompt_tokens:,}p + {completion_tokens:,}c = {tot:,} | {duration_ms}ms")
        except Exception as err:
            logger.warning(f"[PipelineLogger] llm_call error: {err}")

    @staticmethod
    def finish(trace_id: str, session_id: str, query: str, intent_name: str, account_name: str,
               data_quality_pct: float, confidence_pct: float, duration_ms: int, status: str = "SUCCESS"):
        try:
            snapshot = TokenAccumulator.snapshot()
            border = "=" * 66
            dq_pct = float(data_quality_pct or 100.0)
            conf_pct = float(confidence_pct or 100.0)
            
            logger.info(f"+- L3 LLM SUMMARY ────────────────────────────────────────────────+")
            for call in snapshot["calls"]:
                logger.info(f"|  • {call['call_name']:<22} : {call['prompt_tokens']:,}p + {call['completion_tokens']:,}c = {call['total_tokens']:,} tkn (${call['cost_usd']:.6f}) |")
            logger.info(f"+-----------------------------------------------------------------+")

            logger.info(f"\n+{border}+")
            logger.info(f"|  APEX PIPELINE COMPLETE  |  Status: {status:<10} Duration: {duration_ms}ms  |")
            logger.info(f"+{border}+")
            logger.info(f"|  LLM Calls    : {snapshot['total_llm_calls']:<3}                                           |")
            logger.info(f"|  Prompt Tokens: {snapshot['prompt_tokens']:,:<12} Completion Tokens: {snapshot['completion_tokens']:,:<10} |")
            logger.info(f"|  Total Tokens : {snapshot['total_tokens']:,:<12} Est. Cost (Flash): ${snapshot['estimated_cost_usd']:.6f} |")
            logger.info(f"|  Confidence   : {conf_pct:.1f}%        Data Quality     : {dq_pct:.1f}%          |")
            logger.info(f"+{border}+\n")
        except Exception as finish_err:
            logger.warning(f"[PipelineLogger] finish formatting error: {finish_err}")

        # Write structured JSONL record to logs/eval_YYYY-MM-DD.jsonl (indefinite history)
        try:
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            today_str = datetime.now().strftime("%Y-%m-%d")
            eval_file = os.path.join(logs_dir, f"eval_{today_str}.jsonl")

            eval_record = {
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id,
                "session_id": session_id,
                "query": query,
                "intent": intent_name,
                "account": account_name,
                "status": status,
                "duration_ms": duration_ms,
                "data_quality_pct": round(data_quality_pct, 1),
                "confidence_pct": round(confidence_pct, 1),
                "prompt_tokens": snapshot["prompt_tokens"],
                "completion_tokens": snapshot["completion_tokens"],
                "total_tokens": snapshot["total_tokens"],
                "estimated_cost_usd": snapshot["estimated_cost_usd"],
                "llm_calls_count": snapshot["total_llm_calls"],
                "call_details": snapshot["calls"]
            }

            with open(eval_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(eval_record) + "\n")
        except Exception as eval_err:
            logger.warning(f"[PipelineLogger] Failed to write eval JSONL record: {eval_err}")
