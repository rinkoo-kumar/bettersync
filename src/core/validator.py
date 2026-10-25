"""
Pre-Flight Data Validator & Schema Normalizer
Catches bad data before it cascades across Workday, Okta, and ExpoIT.
"""

from typing import Any, Dict, List, Optional, Tuple
import re
from ..models.canonical import Address, HireProfile


class ValidationError(Exception):
    def __init__(self, field: str, message: str, code: str = "INVALID_FIELD"):
        super().__init__(f"Validation failure on '{field}': {message}")
        self.field = field
        self.code = code


class DataValidator:
    US_ZIP_REGEX = re.compile(r"^\d{5}(-\d{4})?$")
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    @classmethod
    def validate_profile(cls, profile: HireProfile) -> List[str]:
        """Runs pre-flight validation checks. Returns list of warning or invariant violations."""
        issues: List[str] = []

        # Invariant 1: First and Last Name must not contain placeholder characters or typos
        if re.search(r"[0-9!@#$%^&*()_+=\[\]{};:\"\\|,.<>/?]", profile.first_name):
            issues.append(f"First name '{profile.first_name}' contains suspicious characters.")
        if re.search(r"[0-9!@#$%^&*()_+=\[\]{};:\"\\|,.<>/?]", profile.last_name):
            issues.append(f"Last name '{profile.last_name}' contains suspicious characters.")

        # Invariant 2: Email domains
        if not cls.EMAIL_REGEX.match(profile.email):
            issues.append(f"Corporate email '{profile.email}' is malformed.")
        if not profile.email.endswith("@betterup.co"):
            issues.append(f"Corporate email '{profile.email}' must use @betterup.co domain.")

        # Invariant 3: Address completeness for physical hardware dispatch
        addr = profile.address
        if not addr.street1 or len(addr.street1.strip()) < 3:
            issues.append("Shipping address street line 1 is missing or too short.")
        if addr.country == "US" and not cls.US_ZIP_REGEX.match(addr.postal_code):
            issues.append(f"Invalid US ZIP code '{addr.postal_code}'. Must be 5 digits or ZIP+4.")
        if addr.country == "US" and len(addr.state) != 2:
            issues.append(f"US State code '{addr.state}' must be a 2-letter abbreviation.")

        # Invariant 4: Start date must be valid ISO format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", profile.start_date):
            issues.append(f"Start date '{profile.start_date}' is not a valid YYYY-MM-DD format.")

        return issues

    @classmethod
    def sanitize_name(cls, name: str) -> str:
        """Strip spurious whitespace and title-case."""
        clean = " ".join(name.strip().split())
        return clean.title()

    @classmethod
    def normalize_address(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes common street abbreviations and casings."""
        street1 = raw.get("street1", "").strip()
        
        # Expand common USPS standard abbreviations if needed
        street_replacements = {
            r"\bSt\b\.?": "Street",
            r"\bAve\b\.?": "Avenue",
            r"\bBlvd\b\.?": "Boulevard",
            r"\bRd\b\.?": "Road",
            r"\bDr\b\.?": "Drive",
            r"\bApt\b\.?": "Apt",
            r"\bSte\b\.?": "Suite",
        }
        for pattern, repl in street_replacements.items():
            street1 = re.sub(pattern, repl, street1, flags=re.IGNORECASE)

        return {
            "street1": street1,
            "street2": raw.get("street2", "").strip() or None,
            "city": raw.get("city", "").strip().title(),
            "state": raw.get("state", "").strip().upper()[:2],
            "postal_code": raw.get("postal_code", "").strip(),
            "country": raw.get("country", "US").strip().upper()[:2]
        }
