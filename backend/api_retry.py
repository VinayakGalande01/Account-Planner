"""
APEX LLM API Retry Utility with Exponential Backoff and Jitter.
"""

import time
import random
import logging

logger = logging.getLogger("backend")

def call_with_backoff(fn, *args, max_retries: int = 3, base_delay: float = 2.0, **kwargs):
    """
    Executes a synchronous function with exponential backoff and jitter.
    Fails after max_retries attempts.
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exception = e
            # Check if this looks like a transient rate-limit or demand spike error
            err_msg = str(e).lower()
            is_transient = any(msg in err_msg for msg in ["503", "unavailable", "rate limit", "quota", "429", "timeout"])
            
            if attempt == max_retries:
                logger.error(f"[API Retry] Attempt {attempt}/{max_retries} failed. Max retries reached. Error: {e}")
                raise e
            
            # Calculate backoff: base_delay * 2^(attempt-1) + jitter
            delay = base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0.1, 0.5)
            total_delay = delay + jitter
            
            log_level = logging.WARNING if is_transient else logging.ERROR
            logger.log(
                log_level,
                f"[API Retry] Attempt {attempt}/{max_retries} failed. Retrying in {total_delay:.2f}s... Error: {e}"
            )
            time.sleep(total_delay)
            
    if last_exception:
        raise last_exception
