"""
Model Context Protocol (MCP) Tool Specifications for BetterUp People Systems.
These definitions allow Claude Desktop, Claude Code, or Cursor to inspect and resolve
People Ops state using standard JSON-RPC MCP calls.
"""

from typing import Any, Dict, List

MCP_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "get_hire_cross_system_state",
        "description": "Fetches the synchronized state of a hire across Ashby, Workday, Okta, and ExpoIT.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hire_id": {
                    "type": "string",
                    "description": "Canonical hire ID (e.g. HIRE-1001) or Ashby/Workday ID."
                }
            },
            "required": ["hire_id"]
        }
    },
    {
        "name": "compute_system_drift",
        "description": "Calculates semantic diffs and discrepancies between Workday, Ashby, and downstream systems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hire_id": {
                    "type": "string",
                    "description": "Canonical hire ID to evaluate for drift."
                }
            },
            "required": ["hire_id"]
        }
    },
    {
        "name": "resolve_discrepancy_and_sync",
        "description": "Applies an approved resolution to a field discrepancy and propagates the change idempotently.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hire_id": {
                    "type": "string",
                    "description": "Canonical hire ID."
                },
                "field_name": {
                    "type": "string",
                    "description": "Field to reconcile (e.g. 'address', 'start_date', 'preferred_name')."
                },
                "authoritative_value": {
                    "description": "The reconciled value to write to target systems."
                },
                "target_systems": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of systems to update (e.g. ['workday', 'expoit', 'okta'])."
                },
                "rationale": {
                    "type": "string",
                    "description": "Engineering or AI justification recorded in the audit trail."
                }
            },
            "required": ["hire_id", "field_name", "authoritative_value", "target_systems", "rationale"]
        }
    },
    {
        "name": "evaluate_sla_gates",
        "description": "Evaluates all upcoming onboarding milestones against T-7, T-4, and T-3 deadlines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cohort_name": {
                    "type": "string",
                    "description": "Optional cohort filter (e.g. '2026-11-A'). If omitted, evaluates all active hires."
                }
            }
        }
    },
    {
        "name": "notify_people_ops_slack",
        "description": "Dispatches an interactive triage card or urgent alert to the People Operations Slack channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel name (e.g. '#people-ops-triage')."
                },
                "headline": {
                    "type": "string",
                    "description": "Alert title or subject."
                },
                "body_markdown": {
                    "type": "string",
                    "description": "Detailed markdown explanation with recommended actions."
                },
                "severity": {
                    "type": "string",
                    "enum": ["INFO", "WARNING", "CRITICAL"],
                    "description": "Alert severity level."
                }
            },
            "required": ["channel", "headline", "body_markdown", "severity"]
        }
    }
]
