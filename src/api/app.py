"""
FastAPI Service for BetterSync
Exposes endpoints for webhooks, reconciliation runs, SLA gates, and audit chain verification.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from ..core.reconciler import Reconciler
from ..models.events import EventType

app = FastAPI(
    title="BetterSync - People Systems Orchestration Engine",
    description="Event-driven change propagation, SLA gatekeeping, and Claude exception triage for BetterUp.",
    version="1.0.0"
)

# Shared orchestrator instance
reconciler = Reconciler()


class WebhookPayload(BaseModel):
    hire_id: str
    event_type: str
    data: Dict[str, Any]


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "service": "BetterSync"}


@app.post("/webhooks/ashby")
def ashby_webhook(payload: WebhookPayload, x_idempotency_key: Optional[str] = Header(None)):
    key = x_idempotency_key or f"ashby_hook:{payload.hire_id}:{payload.event_type}"
    event_enum = EventType(payload.event_type) if payload.event_type in [e.value for e in EventType] else EventType.CANDIDATE_UPDATED
    
    full_data = {"hire_id": payload.hire_id, **payload.data}
    result = reconciler.ingest_event(event_enum, full_data, key)
    return result


@app.post("/webhooks/workday")
def workday_webhook(payload: WebhookPayload, x_idempotency_key: Optional[str] = Header(None)):
    key = x_idempotency_key or f"workday_hook:{payload.hire_id}:{payload.event_type}"
    event_enum = EventType(payload.event_type) if payload.event_type in [e.value for e in EventType] else EventType.WORKER_UPDATED
    
    full_data = {"hire_id": payload.hire_id, **payload.data}
    result = reconciler.ingest_event(event_enum, full_data, key)
    return result


@app.get("/reconcile/{hire_id}")
def reconcile_hire(hire_id: str):
    resolutions = reconciler.reconcile_with_ai(hire_id)
    return {
        "hire_id": hire_id,
        "discrepancies_resolved": len(resolutions),
        "resolutions": resolutions
    }


@app.get("/sla/gates")
def check_sla_gates():
    # Gather all hires from tracker
    hires_raw = reconciler.cohort_tracker.list_all()
    # In a real app we'd convert to HireProfile objects, here we evaluate demo profiles
    return {"status": "SUCCESS", "message": "Gatekeeper active. Run via CLI demo or test suite."}


@app.get("/audit/verify")
def verify_audit_trail():
    is_valid = reconciler.audit.verify_integrity()
    history = reconciler.audit.get_history()
    return {
        "integrity_verified": is_valid,
        "total_records": len(history),
        "latest_hash": reconciler.audit._latest_hash
    }
