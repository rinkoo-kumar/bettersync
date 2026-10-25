"""
Workday HCM Connector (Mocked API)
Represents Core HCM Worker endpoints, supporting standard and off-cycle hires.
"""

from typing import Any, Dict, Optional
import copy
from .base import BaseConnector, ConnectorException


class WorkdayConnector(BaseConnector):
    def __init__(self):
        super().__init__("workday")

    def seed(self, records: Dict[str, Dict[str, Any]]):
        self._records = copy.deepcopy(records)

    def get_record(self, worker_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        return self._records.get(worker_id)

    def get_by_hire_id(self, hire_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        for worker in self._records.values():
            if worker.get("hire_id") == hire_id:
                return worker
        return None

    def create_or_update(self, worker_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        self._check_simulation()
        
        if self.is_idempotent(idempotency_key):
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "data": self._records.get(worker_id)
            }

        existing = self._records.get(worker_id, {})
        updated = {**existing, **data, "worker_id": worker_id}
        self._records[worker_id] = updated
        self.register_idempotency_key(idempotency_key)

        return {
            "status": "SUCCESS",
            "idempotent": False,
            "data": updated
        }

    def create_off_cycle_worker(self, worker_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        """Simulates an off-cycle contractor/exec created directly in Workday."""
        data["is_off_cycle"] = True
        return self.create_or_update(worker_id, data, idempotency_key)
