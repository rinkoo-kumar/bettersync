"""
Canonical Data Models for BetterSync
Defines the unified HireProfile schema, Address structure, and Invariants.
"""

from __future__ import annotations
import hashlib
import json
import re
from datetime import date
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class HardwareStatus(str, Enum):
    NOT_ORDERED = "NOT_ORDERED"
    FORM_SUBMITTED = "FORM_SUBMITTED"
    ORDERED = "ORDERED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"


class BackgroundCheckStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    CLEARED = "CLEARED"
    FAILED = "FAILED"
    WAIVED = "WAIVED"


class OktaStatus(str, Enum):
    NOT_STAGED = "NOT_STAGED"
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class Address(BaseModel):
    street1: str = Field(..., description="Primary street address")
    street2: Optional[str] = Field(default=None, description="Suite, Apt, Unit")
    city: str
    state: str = Field(..., description="2-letter state code or province")
    postal_code: str = Field(..., description="ZIP code or postal code")
    country: str = Field(default="US", description="ISO-3166-1 alpha-2 code")

    @field_validator("state")
    @classmethod
    def normalize_state(cls, v: str) -> str:
        clean = v.strip().upper()
        # Common full name to 2-letter mapping
        mapping = {
            "CALIFORNIA": "CA", "NEW YORK": "NY", "TEXAS": "TX",
            "WASHINGTON": "WA", "COLORADO": "CO", "ILLINOIS": "IL"
        }
        return mapping.get(clean, clean)

    @field_validator("postal_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        clean = v.strip()
        # Basic 5-digit or 5+4 validation for US
        digits = re.sub(r"[^\d]", "", clean)
        if len(digits) == 9:
            return f"{digits[:5]}-{digits[5:]}"
        elif len(digits) == 5:
            return digits
        return clean

    def standardized_string(self) -> str:
        apt = f" {self.street2}" if self.street2 else ""
        return f"{self.street1}{apt}, {self.city}, {self.state} {self.postal_code}, {self.country}".strip().upper()


class HireProfile(BaseModel):
    """
    Canonical representation of a hire synchronized across Ashby, Workday, Okta, and ExpoIT.
    """
    hire_id: str = Field(..., description="Global canonical identifier, e.g. HIRE-1001")
    ashby_id: Optional[str] = Field(default=None, description="Ashby Candidate/Application ID")
    workday_id: Optional[str] = Field(default=None, description="Workday Worker ID (WKD-xxx)")
    okta_id: Optional[str] = Field(default=None, description="Okta User ID")
    
    first_name: str
    last_name: str
    preferred_name: Optional[str] = None
    email: str = Field(..., description="Corporate primary email")
    personal_email: str = Field(..., description="Personal email used during recruitment")
    phone: Optional[str] = None
    
    role_title: str
    department: str
    manager_email: str
    start_date: str = Field(..., description="ISO-8601 start date (YYYY-MM-DD)")
    
    address: Address
    
    hardware_sku: Optional[str] = Field(default="MBP-14-M3-36GB", description="Assigned laptop SKU")
    hardware_status: HardwareStatus = HardwareStatus.NOT_ORDERED
    hardware_tracking_number: Optional[str] = None
    it_hardware_form_completed: bool = False
    
    background_check_status: BackgroundCheckStatus = BackgroundCheckStatus.NOT_STARTED
    okta_status: OktaStatus = OktaStatus.NOT_STAGED
    cohort_name: str = Field(default="General", description="Onboarding cohort name (e.g., '2026-11-A')")
    
    version: int = Field(default=1, description="Optimistic locking version counter")

    @field_validator("email", "personal_email", "manager_email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError(f"Invalid email format: {clean}")
        return clean

    @property
    def display_name(self) -> str:
        name = self.preferred_name if self.preferred_name else self.first_name
        return f"{name} {self.last_name}"

    def compute_hash(self) -> str:
        """Computes a deterministic SHA-256 fingerprint of mutable fields to detect drift."""
        data = {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "preferred_name": self.preferred_name,
            "start_date": self.start_date,
            "address": self.address.model_dump(),
            "department": self.department,
            "role_title": self.role_title,
            "hardware_status": self.hardware_status.value,
            "bg_status": self.background_check_status.value,
            "okta_status": self.okta_status.value,
        }
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
