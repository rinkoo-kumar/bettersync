"""
Core Reconciliation & Change Propagation Engine
Coordinates multi-system sync, idempotency, failure retries, and Claude exception triage.
"""

from __future__ import annotations
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from ..connectors import AshbyConnector, WorkdayConnector, OktaConnector, ExpoITConnector, CohortTrackerConnector
from ..models.canonical import HireProfile, Address, HardwareStatus, BackgroundCheckStatus, OktaStatus
from ..models.events import EventType, TargetSystem, ActionType, SyncAction, Discrepancy, DiscrepancySeverity
from ..agent.claude_resolver import ClaudeResolver
from .audit_logger import AuditLogger
from .gatekeeper import SLAGatekeeper, SLABreach
from .validator import DataValidator

logger = logging.getLogger(__name__)


class Reconciler:
    def __init__(
        self,
        ashby: Optional[AshbyConnector] = None,
        workday: Optional[WorkdayConnector] = None,
        okta: Optional[OktaConnector] = None,
        expoit: Optional[ExpoITConnector] = None,
        cohort_tracker: Optional[CohortTrackerConnector] = None,
        audit_logger: Optional[AuditLogger] = None,
        claude_resolver: Optional[ClaudeResolver] = None,
        gatekeeper: Optional[SLAGatekeeper] = None,
    ):
        self.ashby = ashby or AshbyConnector()
        self.workday = workday or WorkdayConnector()
        self.okta = okta or OktaConnector()
        self.expoit = expoit or ExpoITConnector()
        self.cohort_tracker = cohort_tracker or CohortTrackerConnector()
        
        self.audit = audit_logger or AuditLogger()
        self.claude = claude_resolver or ClaudeResolver()
        self.gatekeeper = gatekeeper or SLAGatekeeper()
        
        self._processed_events: set[str] = set()

    def generate_idempotency_key(self, hire_id: str, target_system: str, action: str, payload: Dict[str, Any]) -> str:
        raw = f"{hire_id}:{target_system}:{action}:{json.dumps(payload, sort_keys=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def ingest_event(self, event_type: EventType, payload: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        """Ingests an external webhook or change event with strict idempotency."""
        if idempotency_key in self._processed_events:
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "message": f"Event with idempotency key '{idempotency_key}' was already processed. Skipped."
            }

        hire_id = payload.get("hire_id")
        if not hire_id:
            return {"status": "ERROR", "message": "Missing hire_id in payload"}

        actions_taken = []

        if event_type == EventType.OFFER_SIGNED:
            actions_taken = self._handle_offer_signed(payload, idempotency_key)
        elif event_type in [EventType.START_DATE_UPDATED, EventType.CANDIDATE_UPDATED]:
            actions_taken = self._handle_candidate_updated(payload, idempotency_key)
        elif event_type == EventType.WORKER_CREATED_OFF_CYCLE:
            actions_taken = self._handle_off_cycle_hire(payload, idempotency_key)
        else:
            return {"status": "IGNORED", "message": f"Unsupported event type: {event_type}"}

        self._processed_events.add(idempotency_key)
        
        self.audit.log(
            event_type=event_type.value,
            entity_id=hire_id,
            actor=f"webhook.{event_type.value.split('.')[0]}",
            diff=payload,
            decision_rationale=f"Processed event {event_type.value} with {len(actions_taken)} downstream actions.",
            status="SUCCESS"
        )

        return {
            "status": "SUCCESS",
            "hire_id": hire_id,
            "actions_taken": actions_taken
        }

    def _handle_offer_signed(self, payload: Dict[str, Any], parent_key: str) -> List[Dict[str, Any]]:
        hire_id = payload["hire_id"]
        actions = []

        # 1. Normalize and validate address
        raw_address = payload.get("address", {})
        norm_address = DataValidator.normalize_address(raw_address)
        payload["address"] = norm_address

        # 2. Push to Workday
        wkd_key = f"{parent_key}:workday"
        wkd_res = self.workday.create_or_update(hire_id, payload, wkd_key)
        actions.append({"system": "workday", "result": wkd_res})

        # 3. Stage in Okta
        okta_key = f"{parent_key}:okta"
        okta_payload = {
            "hire_id": hire_id,
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": payload.get("email"),
            "department": payload.get("department"),
            "role_title": payload.get("role_title")
        }
        okta_res = self.okta.stage_user(hire_id, okta_payload, payload["start_date"], okta_key)
        actions.append({"system": "okta", "result": okta_res})

        # 4. Create ExpoIT Order
        expo_key = f"{parent_key}:expoit"
        expo_payload = {
            "hire_id": hire_id,
            "employee_name": f"{payload.get('first_name')} {payload.get('last_name')}",
            "hardware_sku": payload.get("hardware_sku", "MBP-14-M3-36GB"),
            "target_delivery_date": payload["start_date"],
            "shipping_address": norm_address,
            "status": "ORDERED"
        }
        expo_res = self.expoit.create_or_update(f"ORD-{hire_id}", expo_payload, expo_key)
        actions.append({"system": "expoit", "result": expo_res})

        # 5. Cohort Tracker
        ct_key = f"{parent_key}:cohort_tracker"
        ct_payload = {
            "hire_id": hire_id,
            "name": f"{payload.get('first_name')} {payload.get('last_name')}",
            "role_title": payload.get("role_title"),
            "department": payload.get("department"),
            "start_date": payload["start_date"],
            "cohort_name": payload.get("cohort_name", "General"),
            "readiness_status": "PENDING_GATES"
        }
        ct_res = self.cohort_tracker.create_or_update(hire_id, ct_payload, ct_key)
        actions.append({"system": "cohort_tracker", "result": ct_res})

        return actions

    def _handle_candidate_updated(self, payload: Dict[str, Any], parent_key: str) -> List[Dict[str, Any]]:
        hire_id = payload["hire_id"]
        actions = []

        # Check for start date change
        new_start_date = payload.get("start_date")
        if new_start_date:
            wkd_key = f"{parent_key}:wkd_date"
            self.workday.create_or_update(hire_id, {"start_date": new_start_date}, wkd_key)
            actions.append({"system": "workday", "field": "start_date", "new_value": new_start_date})

            # Reschedule Okta activation
            okta_key = f"{parent_key}:okta_date"
            self.okta.create_or_update(hire_id, {"scheduled_activation": f"{new_start_date}T06:00:00Z"}, okta_key)
            actions.append({"system": "okta", "field": "scheduled_activation", "new_value": new_start_date})

            # Reschedule ExpoIT delivery
            expo_key = f"{parent_key}:expo_date"
            order = self.expoit.get_by_hire_id(hire_id)
            if order:
                self.expoit.reschedule_shipment(order["order_id"], new_start_date, expo_key)
                actions.append({"system": "expoit", "field": "target_delivery_date", "new_value": new_start_date})

            # Update Tracker
            ct_key = f"{parent_key}:ct_date"
            self.cohort_tracker.create_or_update(hire_id, {"start_date": new_start_date}, ct_key)
            actions.append({"system": "cohort_tracker", "field": "start_date", "new_value": new_start_date})

        # Check for address change
        new_address = payload.get("address")
        if new_address:
            norm = DataValidator.normalize_address(new_address)
            wkd_key = f"{parent_key}:wkd_addr"
            self.workday.create_or_update(hire_id, {"address": norm}, wkd_key)
            actions.append({"system": "workday", "field": "address", "new_value": norm})

            expo_key = f"{parent_key}:expo_addr"
            order = self.expoit.get_by_hire_id(hire_id)
            if order:
                self.expoit.update_shipping_address(order["order_id"], norm, expo_key)
                actions.append({"system": "expoit", "field": "shipping_address", "new_value": norm})

        return actions

    def _handle_off_cycle_hire(self, payload: Dict[str, Any], parent_key: str) -> List[Dict[str, Any]]:
        """Handles hire created directly in Workday, bypassing Ashby."""
        hire_id = payload["hire_id"]
        actions = []

        # 1. Record in Workday
        wkd_key = f"{parent_key}:wkd_off_cycle"
        wkd_res = self.workday.create_off_cycle_worker(hire_id, payload, wkd_key)
        actions.append({"system": "workday", "result": wkd_res})

        # 2. Stage in Okta
        okta_key = f"{parent_key}:okta_off_cycle"
        okta_payload = {
            "hire_id": hire_id,
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "email": payload.get("email"),
            "department": payload.get("department"),
            "role_title": payload.get("role_title")
        }
        okta_res = self.okta.stage_user(hire_id, okta_payload, payload["start_date"], okta_key)
        actions.append({"system": "okta", "result": okta_res})

        # 3. Create ExpoIT Order
        expo_key = f"{parent_key}:expo_off_cycle"
        expo_payload = {
            "hire_id": hire_id,
            "employee_name": f"{payload.get('first_name')} {payload.get('last_name')}",
            "hardware_sku": payload.get("hardware_sku", "MBP-14-M3-36GB"),
            "target_delivery_date": payload["start_date"],
            "shipping_address": payload.get("address", {}),
            "status": "ORDERED"
        }
        expo_res = self.expoit.create_or_update(f"ORD-{hire_id}", expo_payload, expo_key)
        actions.append({"system": "expoit", "result": expo_res})

        # 4. Cohort Tracker
        ct_key = f"{parent_key}:ct_off_cycle"
        ct_payload = {
            "hire_id": hire_id,
            "name": f"{payload.get('first_name')} {payload.get('last_name')}",
            "role_title": payload.get("role_title"),
            "department": payload.get("department"),
            "start_date": payload["start_date"],
            "cohort_name": "Off-Cycle",
            "readiness_status": "PENDING_GATES"
        }
        ct_res = self.cohort_tracker.create_or_update(hire_id, ct_payload, ct_key)
        actions.append({"system": "cohort_tracker", "result": ct_res})

        return actions

    def compute_drift(self, hire_id: str) -> List[Discrepancy]:
        """Detects drift between Ashby (ATS), Workday (HRIS), Okta (IdP), and ExpoIT."""
        discrepancies: List[Discrepancy] = []
        
        ashby_rec = self.ashby.get_by_hire_id(hire_id)
        wkd_rec = self.workday.get_by_hire_id(hire_id)
        okta_rec = self.okta.get_by_hire_id(hire_id)
        expo_rec = self.expoit.get_by_hire_id(hire_id)

        if not ashby_rec or not wkd_rec:
            return discrepancies

        # Compare Start Date
        if ashby_rec.get("start_date") != wkd_rec.get("start_date"):
            discrepancies.append(Discrepancy(
                hire_id=hire_id,
                field_name="start_date",
                source_system="ashby",
                source_value=ashby_rec.get("start_date"),
                target_system="workday",
                target_value=wkd_rec.get("start_date"),
                severity=DiscrepancySeverity.HIGH,
                requires_ai_triage=True
            ))

        # Compare Address
        ashby_addr = ashby_rec.get("address", {})
        wkd_addr = wkd_rec.get("address", {})
        if ashby_addr != wkd_addr:
            discrepancies.append(Discrepancy(
                hire_id=hire_id,
                field_name="address",
                source_system="ashby",
                source_value=ashby_addr,
                target_system="workday",
                target_value=wkd_addr,
                severity=DiscrepancySeverity.MEDIUM,
                requires_ai_triage=True
            ))

        # Compare Names
        if ashby_rec.get("first_name") != wkd_rec.get("first_name"):
            discrepancies.append(Discrepancy(
                hire_id=hire_id,
                field_name="first_name",
                source_system="ashby",
                source_value=ashby_rec.get("first_name"),
                target_system="workday",
                target_value=wkd_rec.get("first_name"),
                severity=DiscrepancySeverity.MEDIUM,
                requires_ai_triage=True
            ))

        return discrepancies

    def reconcile_with_ai(self, hire_id: str) -> List[Dict[str, Any]]:
        """Finds discrepancies, uses Claude to reason and resolve them, and executes sync."""
        discrepancies = self.compute_drift(hire_id)
        resolutions = []

        context = {
            "hire_id": hire_id,
            "ashby": self.ashby.get_by_hire_id(hire_id),
            "workday": self.workday.get_by_hire_id(hire_id),
            "expoit": self.expoit.get_by_hire_id(hire_id),
            "okta": self.okta.get_by_hire_id(hire_id)
        }

        for disc in discrepancies:
            resolution = self.claude.resolve_discrepancy(disc, context)
            resolutions.append(resolution)

            if resolution.get("can_auto_resolve"):
                field = resolution["field_name"]
                val = resolution["resolved_value"]
                
                # Apply to target systems
                for target in resolution.get("target_systems_to_update", []):
                    key = f"ai_reconcile:{hire_id}:{field}:{target}"
                    if target == "workday":
                        self.workday.create_or_update(hire_id, {field: val}, key)
                    elif target == "okta":
                        if field == "start_date":
                            self.okta.create_or_update(hire_id, {"scheduled_activation": f"{val}T06:00:00Z"}, key)
                    elif target == "expoit":
                        order = self.expoit.get_by_hire_id(hire_id)
                        if order:
                            if field == "start_date":
                                self.expoit.reschedule_shipment(order["order_id"], val, key)
                            elif field == "address":
                                self.expoit.update_shipping_address(order["order_id"], val, key)
                    elif target == "cohort_tracker":
                        self.cohort_tracker.create_or_update(hire_id, {field: val}, key)

                # Record in tamper-evident audit log
                self.audit.log(
                    event_type="ai_discrepancy_resolved",
                    entity_id=hire_id,
                    actor="claude_agent",
                    diff={"field": field, "resolved_value": val},
                    decision_rationale=resolution.get("analysis"),
                    status="AUTO_RESOLVED"
                )

        return resolutions
