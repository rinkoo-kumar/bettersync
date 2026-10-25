"""
Ashby ATS Connector (Mocked API)
Handles candidate profiles, accepted offers, and change events.
"""

from typing import Any, Dict, Optional
import copy
from .base import BaseConnector, ConnectorException


class AshbyConnector(BaseConnector):
    def __init__(self):
        super().__init__("ashby")

    def seed(self, records: Dict[str, Dict[str, Any]]):
        self._records = copy.deepcopy(records)

    def get_record(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        return self._records.get(candidate_id)

    def get_by_hire_id(self, hire_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        for cand in self._records.values():
            if cand.get("hire_id") == hire_id or cand.get("id") == hire_id:
                return cand
        return None

    def create_or_update(self, candidate_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        self._check_simulation()
        
        if self.is_idempotent(idempotency_key):
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "data": self._records.get(candidate_id)
            }

        existing = self._records.get(candidate_id, {})
        updated = {**existing, **data, "id": candidate_id}
        self._records[candidate_id] = updated
        self.register_idempotency_key(idempotency_key)

        return {
            "status": "SUCCESS",
            "idempotent": False,
            "data": updated
        }

    def update_start_date(self, candidate_id: str, new_start_date: str, idempotency_key: str) -> Dict[str, Any]:
        return self.create_or_update(candidate_id, {"start_date": new_start_date}, idempotency_key)

    def update_address(self, candidate_id: str, address_data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        return self.create_or_update(candidate_id, {"address": address_data}, idempotency_key)
