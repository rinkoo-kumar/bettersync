"""
Base Connector Interface for External Enterprise People Systems
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ConnectorException(Exception):
    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class BaseConnector(ABC):
    def __init__(self, system_name: str):
        self.system_name = system_name
        self._processed_idempotency_keys: Set[str] = set()
        self._simulate_failure: bool = False
        self._failure_count: int = 0
        self._records: Dict[str, Dict[str, Any]] = {}

    def set_simulated_failure(self, enable: bool = True, failure_count: int = 1):
        """Simulate transient API failure (e.g. 503 or 429) for testing resilience."""
        self._simulate_failure = enable
        self._failure_count = failure_count

    def _check_simulation(self):
        if self._simulate_failure and self._failure_count > 0:
            self._failure_count -= 1
            if self._failure_count == 0:
                self._simulate_failure = False
            raise ConnectorException(
                f"[{self.system_name}] Simulated transient 503 Service Unavailable",
                status_code=503,
                retryable=True
            )

    def is_idempotent(self, key: str) -> bool:
        return key in self._processed_idempotency_keys

    def register_idempotency_key(self, key: str):
        self._processed_idempotency_keys.add(key)

    @abstractmethod
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_or_update(self, record_id: str, data: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        pass

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._records.values())
