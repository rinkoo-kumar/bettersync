"""
ExpoIT Hardware & Logistics Connector (Mocked API)
Handles laptop ordering, address updates, shipping schedules, and tracking numbers.
"""

from typing import Any, Dict, Optional
import copy
from .base import BaseConnector, ConnectorException


class ExpoITConnector(BaseConnector):
    def __init__(self):
        super().__init__("expoit")

    def seed(self, records: Dict[str, Dict[str, Any]]):
        self._records = copy.deepcopy(records)

    def get_record(self, order_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        return self._records.get(order_id)

    def get_by_hire_id(self, hire_id: str) -> Optional[Dict[str, Any]]:
        self._check_simulation()
        for order in self._records.values():
            if order.get("hire_id") == hire_id:
                return order
        return None

    def create_or_update(self, order_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        self._check_simulation()
        
        if self.is_idempotent(idempotency_key):
            return {
                "status": "ALREADY_PROCESSED",
                "idempotent": True,
                "data": self._records.get(order_id)
            }

        existing = self._records.get(order_id, {})
        updated = {**existing, **data, "order_id": order_id}
        self._records[order_id] = updated
        self.register_idempotency_key(idempotency_key)

        return {
            "status": "SUCCESS",
            "idempotent": False,
            "data": updated
        }

    def update_shipping_address(self, order_id: str, address: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        return self.create_or_update(order_id, {"shipping_address": address}, idempotency_key)

    def reschedule_shipment(self, order_id: str, new_target_delivery_date: str, idempotency_key: str) -> Dict[str, Any]:
        return self.create_or_update(order_id, {"target_delivery_date": new_target_delivery_date}, idempotency_key)
