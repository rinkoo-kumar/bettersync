"""
SLA Gatekeeper & Invariant Watcher
Monitors time-sensitive onboarding milestones (T-7 days, T-4 days, T-3 days)
and triggers proactive alerts and auto-remediations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from ..models.canonical import BackgroundCheckStatus, HardwareStatus, HireProfile, OktaStatus


class SLABreach:
    def __init__(self, hire_id: str, candidate_name: str, gate_name: str, days_to_start: int, severity: str, message: str, recommended_action: str):
        self.hire_id = hire_id
        self.candidate_name = candidate_name
        self.gate_name = gate_name
        self.days_to_start = days_to_start
        self.severity = severity
        self.message = message
        self.recommended_action = recommended_action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hire_id": self.hire_id,
            "candidate_name": self.candidate_name,
            "gate_name": self.gate_name,
            "days_to_start": self.days_to_start,
            "severity": self.severity,
            "message": self.message,
            "recommended_action": self.recommended_action
        }

    def to_slack_block(self) -> Dict[str, Any]:
        emoji = ":rotating_light:" if self.severity == "CRITICAL" else ":warning:"
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{emoji} *SLA Breach on Gate: {self.gate_name}* (T-{self.days_to_start}d)\n"
                    f"*Candidate:* {self.candidate_name} (`{self.hire_id}`)\n"
                    f"*Issue:* {self.message}\n"
                    f"*Action Required:* {self.recommended_action}"
                )
            }
        }


class SLAGatekeeper:
    def __init__(self, reference_date: Optional[date] = None):
        self.reference_date = reference_date or date.today()

    def set_reference_date(self, ref_date: date):
        self.reference_date = ref_date

    def evaluate_hire(self, hire: HireProfile) -> List[SLABreach]:
        """Evaluates time-based gates for a single hire against the reference date."""
        breaches: List[SLABreach] = []
        
        try:
            hire_start = datetime.strptime(hire.start_date, "%Y-%m-%d").date()
        except ValueError:
            return breaches

        days_to_start = (hire_start - self.reference_date).days

        # Gate 1: IT Hardware Form Deadline (T-7 days)
        if days_to_start <= 7 and not hire.it_hardware_form_completed:
            severity = "CRITICAL" if days_to_start <= 4 else "HIGH"
            breaches.append(SLABreach(
                hire_id=hire.hire_id,
                candidate_name=hire.display_name,
                gate_name="IT Hardware Form",
                days_to_start=days_to_start,
                severity=severity,
                message=f"IT Hardware Selection form not completed. Start date is {hire.start_date} ({days_to_start} days away).",
                recommended_action="Dispatch automated Slack nudge to candidate/manager or auto-default to standard laptop SKU."
            ))

        # Gate 2: Background Check Clearance (T-7 days)
        if days_to_start <= 7 and hire.background_check_status not in [BackgroundCheckStatus.CLEARED, BackgroundCheckStatus.WAIVED]:
            severity = "CRITICAL" if days_to_start <= 3 else "HIGH"
            breaches.append(SLABreach(
                hire_id=hire.hire_id,
                candidate_name=hire.display_name,
                gate_name="Background Check Clearance",
                days_to_start=days_to_start,
                severity=severity,
                message=f"Background check status is '{hire.background_check_status.value}'. Must be CLEARED >= 7 days prior.",
                recommended_action="Escalate to People Ops Talent Partner to contact background check vendor or delay start date."
            ))

        # Gate 3: Hardware Dispatch & Tracking (T-4 days)
        if days_to_start <= 4 and hire.hardware_status not in [HardwareStatus.SHIPPED, HardwareStatus.DELIVERED]:
            breaches.append(SLABreach(
                hire_id=hire.hire_id,
                candidate_name=hire.display_name,
                gate_name="Hardware Logistics",
                days_to_start=days_to_start,
                severity="CRITICAL",
                message=f"Hardware is in state '{hire.hardware_status.value}' with no tracking number. Start date is in {days_to_start} days.",
                recommended_action="Trigger emergency overnight courier dispatch ticket with ExpoIT logistics."
            ))

        # Gate 4: Okta Identity Provisioning (T-3 days)
        if days_to_start <= 3 and hire.okta_status not in [OktaStatus.STAGED, OktaStatus.ACTIVE]:
            breaches.append(SLABreach(
                hire_id=hire.hire_id,
                candidate_name=hire.display_name,
                gate_name="Okta Identity Staging",
                days_to_start=days_to_start,
                severity="HIGH",
                message=f"Okta user account is '{hire.okta_status.value}'. Account must be staged >= 3 days before Day 1.",
                recommended_action="Run automated Okta provisioning job to stage account and schedule Day 1 activation."
            ))

        return breaches

    def evaluate_all(self, hires: List[HireProfile]) -> List[SLABreach]:
        all_breaches = []
        for hire in hires:
            all_breaches.extend(self.evaluate_hire(hire))
        return all_breaches
