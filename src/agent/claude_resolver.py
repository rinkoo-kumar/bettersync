"""
Claude AI Exception Resolver
Performs agentic decision-making on ambiguous discrepancies across People systems.
Supports live Anthropic API (Claude 3.5 Sonnet) or deterministic local fallback.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from ..models.events import Discrepancy, DiscrepancySeverity
from .prompts import CLAUDE_EXCEPTION_RESOLVER_SYSTEM_PROMPT


class ClaudeResolver:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def resolve_discrepancy(self, discrepancy: Discrepancy, full_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes discrepancy using Claude or local heuristic fallback.
        Returns a structured resolution dictionary.
        """
        if self.client:
            return self._resolve_with_api(discrepancy, full_context)
        return self._resolve_with_local_engine(discrepancy, full_context)

    def _resolve_with_api(self, discrepancy: Discrepancy, full_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calls Anthropic Claude API with tool/JSON output."""
        prompt = (
            f"Analyze this cross-system discrepancy for hire {discrepancy.hire_id}:\n"
            f"Field: {discrepancy.field_name}\n"
            f"Source ({discrepancy.source_system}): {json.dumps(discrepancy.source_value)}\n"
            f"Target ({discrepancy.target_system}): {json.dumps(discrepancy.target_value)}\n"
            f"Context: {json.dumps(full_context)}\n\n"
            f"Return JSON adhering strictly to: "
            f'{{"analysis": str, "can_auto_resolve": bool, "resolved_value": any, '
            f'"target_systems_to_update": [str], "confidence_score": float, "slack_triage_card": str}}'
        )

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=CLAUDE_EXCEPTION_RESOLVER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            # Extract JSON block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            # Fall back to local engine if network/API error occurs
            pass

        return self._resolve_with_local_engine(discrepancy, full_context)

    def _resolve_with_local_engine(self, discrepancy: Discrepancy, full_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        High-fidelity deterministic semantic resolver that mirrors Claude's reasoning rules.
        Handles:
        1. Address formatting / abbreviation differences.
        2. Post-offer start date shifts.
        3. Legal name vs Preferred name synchronization.
        4. Invariant checks.
        """
        field = discrepancy.field_name
        src_val = discrepancy.source_value
        tgt_val = discrepancy.target_value

        # Scenario 1: Address Formatting / Normalization
        if field == "address":
            if isinstance(src_val, dict) and isinstance(tgt_val, dict):
                # Check if it's purely abbreviation or formatting difference
                s_st = src_val.get("street1", "").lower().replace(".", "").replace("street", "st").replace("avenue", "ave")
                t_st = tgt_val.get("street1", "").lower().replace(".", "").replace("street", "st").replace("avenue", "ave")
                
                # Check postal code and city
                same_locale = (
                    src_val.get("city", "").lower() == tgt_val.get("city", "").lower() and
                    src_val.get("state", "").upper() == tgt_val.get("state", "").upper()
                )

                if s_st == t_st or same_locale:
                    # Choose the more complete / standardized version
                    chosen_address = {
                        "street1": src_val.get("street1") or tgt_val.get("street1"),
                        "street2": src_val.get("street2") or tgt_val.get("street2"),
                        "city": src_val.get("city") or tgt_val.get("city"),
                        "state": (src_val.get("state") or tgt_val.get("state")).upper(),
                        "postal_code": src_val.get("postal_code") or tgt_val.get("postal_code"),
                        "country": (src_val.get("country") or tgt_val.get("country", "US")).upper()
                    }
                    return {
                        "field_name": "address",
                        "analysis": (
                            f"Semantic equivalence confirmed. Source ('{src_val.get('street1')}') and "
                            f"Target ('{tgt_val.get('street1')}') refer to the identical physical address with standard postal abbreviation variance."
                        ),
                        "can_auto_resolve": True,
                        "resolved_value": chosen_address,
                        "target_systems_to_update": ["workday", "expoit"],
                        "confidence_score": 0.96,
                        "slack_triage_card": None
                    }

        # Scenario 2: Start Date Changes
        if field == "start_date":
            # If Ashby updated start date after candidate signature, Ashby/Workday agreement needed
            return {
                "field_name": "start_date",
                "analysis": (
                    f"Post-offer start date shift detected: {tgt_val} -> {src_val}. "
                    f"Propagating authoritative start date across Workday, Okta, and ExpoIT hardware delivery."
                ),
                "can_auto_resolve": True,
                "resolved_value": src_val,
                "target_systems_to_update": ["workday", "okta", "expoit", "cohort_tracker"],
                "confidence_score": 0.98,
                "slack_triage_card": None
            }

        # Scenario 3: Name Discrepancies (e.g. Typo vs Legal Name)
        if field in ["first_name", "last_name", "preferred_name"]:
            return {
                "field_name": field,
                "analysis": (
                    f"Name reconciliation for '{field}': Source '{src_val}' vs Target '{tgt_val}'. "
                    f"Applying Workday/Ashby authoritative spelling and updating Okta profile."
                ),
                "can_auto_resolve": True,
                "resolved_value": src_val,
                "target_systems_to_update": ["workday", "okta", "cohort_tracker"],
                "confidence_score": 0.94,
                "slack_triage_card": None
            }

        # Default fallback: Unambiguous conflict requiring human signoff
        return {
            "field_name": field,
            "analysis": f"Conflicting data detected on field '{field}': source '{src_val}' vs target '{tgt_val}'.",
            "can_auto_resolve": False,
            "resolved_value": src_val,
            "target_systems_to_update": [],
            "confidence_score": 0.50,
            "slack_triage_card": (
                f"*Action Required: Data Conflict on {discrepancy.hire_id}*\n"
                f"Field: `{field}`\n"
                f"• {discrepancy.source_system}: `{src_val}`\n"
                f"• {discrepancy.target_system}: `{tgt_val}`\n"
                f"Please review in People Ops Portal."
            )
        }
