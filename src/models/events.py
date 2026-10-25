"""
Event and Discrepancy models for BetterSync.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    OFFER_SIGNED = "ashby.offer_signed"
    CANDIDATE_UPDATED = "ashby.candidate_updated"
    START_DATE_UPDATED = "ashby.start_date_updated"
    WORKER_CREATED_OFF_CYCLE = "workday.worker_created_off_cycle"
    WORKER_UPDATED = "workday.worker_updated"
    SLA_GATE_CHECK = "system.sla_gate_check"
    RECONCILIATION_TRIGGERED = "system.reconciliation_triggered"


class TargetSystem(str, Enum):
    ASHBY = "ashby"
    WORKDAY = "workday"
    OKTA = "okta"
    EXPOIT = "expoit"
    COHORT_TRACKER = "cohort_tracker"
    SLACK = "slack"


class ActionType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    RESCHEDULE = "RESCHEDULE"
    ESCALATE = "ESCALATE"
    NO_OP = "NO_OP"


class SyncAction(BaseModel):
    action_type: ActionType
    target_system: TargetSystem
    hire_id: str
    idempotency_key: str
    payload: Dict[str, Any]
    reason: str
    executed: bool = False
    status: str = "PENDING"
    response: Optional[Dict[str, Any]] = None


class DiscrepancySeverity(str, Enum):
    LOW = "LOW"            # e.g., minor street abbreviation difference
    MEDIUM = "MEDIUM"      # e.g., missing suite number, preferred vs legal name
    HIGH = "HIGH"          # e.g., conflicting start date, invalid address preventing shipping
    CRITICAL = "CRITICAL"  # e.g., missing SSN/Work Auth, SLA breach < 3 days


class Discrepancy(BaseModel):
    hire_id: str
    field_name: str
    source_system: str
    source_value: Any
    target_system: str
    target_value: Any
    severity: DiscrepancySeverity
    requires_ai_triage: bool = False
    proposed_resolution: Optional[Any] = None
    confidence_score: float = 0.0
    resolution_notes: Optional[str] = None
