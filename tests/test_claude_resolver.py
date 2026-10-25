import pytest
from src.agent.claude_resolver import ClaudeResolver
from src.models.events import Discrepancy, DiscrepancySeverity


def test_address_semantic_equivalence():
    resolver = ClaudeResolver()
    disc = Discrepancy(
        hire_id="HIRE-AI-1",
        field_name="address",
        source_system="ashby",
        source_value={"street1": "500 Main St, Ste 200", "city": "Denver", "state": "CO", "postal_code": "80202"},
        target_system="workday",
        target_value={"street1": "500 Main Street Suite 200", "city": "Denver", "state": "CO", "postal_code": "80202"},
        severity=DiscrepancySeverity.MEDIUM
    )
    result = resolver.resolve_discrepancy(disc, full_context={})
    
    assert result["can_auto_resolve"] is True
    assert result["confidence_score"] >= 0.90
    assert "workday" in result["target_systems_to_update"] or "expoit" in result["target_systems_to_update"]


def test_start_date_resolution():
    resolver = ClaudeResolver()
    disc = Discrepancy(
        hire_id="HIRE-AI-2",
        field_name="start_date",
        source_system="ashby",
        source_value="2026-11-20",
        target_system="workday",
        target_value="2026-11-06",
        severity=DiscrepancySeverity.HIGH
    )
    result = resolver.resolve_discrepancy(disc, full_context={})
    
    assert result["can_auto_resolve"] is True
    assert result["resolved_value"] == "2026-11-20"
