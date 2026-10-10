"""Shared pytest fixtures."""
import pytest


@pytest.fixture(autouse=True)
def fixed_reference_date(monkeypatch):
    # Test fixtures use hard-coded mid-2026 dates; pin "today" so staleness checks stay deterministic.
    monkeypatch.setenv("APEX_REFERENCE_DATE", "2026-07-14")
