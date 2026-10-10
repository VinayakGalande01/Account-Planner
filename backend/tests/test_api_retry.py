"""Retry policy: transient errors retry, billing/auth errors fail fast."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_retry import call_with_backoff


def _failing(message, calls):
    def fn():
        calls.append(1)
        raise RuntimeError(message)
    return fn


@pytest.mark.parametrize("message, expected_attempts", [
    ('OpenRouter API error 402: {"error":{"message":"This request requires more credits"}}', 1),
    ("OpenRouter API error 401: invalid api key", 1),
    ("OpenRouter API error 503: unavailable", 3),
    ("OpenRouter API error 429: rate limit", 3),
])
def test_retry_policy(message, expected_attempts):
    calls = []
    with pytest.raises(RuntimeError):
        call_with_backoff(_failing(message, calls), base_delay=0.001)
    assert len(calls) == expected_attempts
