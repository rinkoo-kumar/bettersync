"""
Tamper-Evident Append-Only Audit Logger
Maintains a cryptographically verifiable SHA-256 chain of all sync events and decisions.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from ..models.audit import AuditRecord


class AuditLogger:
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self._entries: List[AuditRecord] = []
        self._latest_hash = self.GENESIS_HASH

    def log(
        self,
        event_type: str,
        entity_id: str,
        actor: str,
        diff: Dict[str, Any],
        decision_rationale: Optional[str] = None,
        target_system: Optional[str] = None,
        status: str = "SUCCESS"
    ) -> AuditRecord:
        record_id = f"aud_{uuid.uuid4().hex[:12]}"
        record = AuditRecord(
            record_id=record_id,
            event_type=event_type,
            entity_id=entity_id,
            actor=actor,
            diff=diff,
            decision_rationale=decision_rationale,
            target_system=target_system,
            status=status,
            prev_hash=self._latest_hash
        )
        record.current_hash = record.calculate_hash()
        self._latest_hash = record.current_hash
        self._entries.append(record)

        if self.log_file:
            self._persist_entry(record)

        return record

    def _persist_entry(self, record: AuditRecord):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

    def verify_integrity(self) -> bool:
        """Verifies that every entry in the chain has not been altered or reordered."""
        if not self._entries:
            return True

        expected_prev_hash = self.GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.prev_hash != expected_prev_hash:
                return False
            recomputed = entry.calculate_hash()
            if entry.current_hash != recomputed:
                return False
            expected_prev_hash = entry.current_hash
        return True

    def get_history(self, entity_id: Optional[str] = None) -> List[AuditRecord]:
        if entity_id:
            return [e for e in self._entries if e.entity_id == entity_id]
        return list(self._entries)
