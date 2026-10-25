"""
Cohort Tracker Connector (Mocked Google Sheets / DB API)
Maintains cohort groupings, checklist completions, and readiness metrics for People Ops.
"""

from typing import Any, Dict, Optional
import copy
from .base import BaseConnector, ConnectorException


class CohortTrackerConnector(BaseConnector):
    def __init__(self):
        super().__init__("cohort_tracker")

    def seed(self, records: Dict[str, Dict[str, Any]]):
        self._records = copy.deepcopy(records)

    def get_record(self, hire_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        return self._records.get(hire_id)

    def create_or_update(self, hire_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        self._check_simulation()
        
        if self.is_idempotent(idempotency_key):
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "data": self._records.get(hire_id)
            }

        existing = self._records.get(hire_id, {})
        updated = {**existing, **data, "hire_id": hire_id}
        self._records[hire_id] = updated
        self.register_idempotency_key(idempotency_key)

        return {
            "status": "SUCCESS",
            "idempotent": False,
            "data": updated
        }
