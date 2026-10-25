"""
Okta / Lumos Identity Connector (Mocked API)
Handles user lifecycle, email generation, account staging, and activation scheduling.
"""

from typing import Any, Dict, Optional
import copy
from .base import BaseConnector, ConnectorException


class OktaConnector(BaseConnector):
    def __init__(self):
        super().__init__("okta")

    def seed(self, records: Dict[str, Dict[str, Any]]):
        self._records = copy.deepcopy(records)

    def get_record(self, okta_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        return self._records.get(okta_id)

    def get_by_hire_id(self, hire_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        for user in self._records.values():
            if user.get("hire_id") == hire_id:
                return user
        return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        for user in self._records.values():
            if user.get("email") == email:
                return user
        return None

    def create_or_update(self, okta_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        self._check_simulation()
        
        if self.is_idempotent(idempotency_key):
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "data": self._records.get(okta_id)
            }

        existing = self._records.get(okta_id, {})
        updated = {**existing, **data, "okta_id": okta_id}
        self._records[okta_id] = updated
        self.register_idempotency_key(idempotency_key)

        return {
            "status": "SUCCESS",
            "idempotent": False,
            "data": updated
        }

    def stage_user(self, okta_id: str, profile_data: Dict[str, Any], activation_date: str, idempotency_key: str) -> Dict[str, Any]:
        payload = {
            **profile_data,
            "status": "STAGED",
            "scheduled_activation": f"{activation_date}T06:00:00Z"
        }
        return self.create_or_update(okta_id, payload, idempotency_key)
