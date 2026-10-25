"""
Cryptographic Tamper-Evident Audit Model
Implements append-only event hashing chaining (prev_hash -> current_hash).
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    record_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str
    entity_id: str
    actor: str  # e.g., "webhook.ashby", "worker.reconciler", "claude_agent", "manual.recruiter"
    diff: Dict[str, Any]
    decision_rationale: Optional[str] = None
    target_system: Optional[str] = None
    status: str = "SUCCESS"
    prev_hash: str
    current_hash: str = ""

    def calculate_hash(self) -> str:
        content = {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "diff": self.diff,
            "decision_rationale": self.decision_rationale,
            "target_system": self.target_system,
            "status": self.status,
            "prev_hash": self.prev_hash
        }
        serialized = json.dumps(content, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
