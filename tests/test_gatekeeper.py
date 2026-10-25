from datetime import date
import pytest
from src.core.gatekeeper import SLAGatekeeper
from src.models.canonical import Address, BackgroundCheckStatus, HardwareStatus, HireProfile, OktaStatus


@pytest.fixture
def base_hire():
    return HireProfile(
        hire_id="HIRE-GATE-1",
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@betterup.co",
        personal_email="jane.personal@gmail.com",
        role_title="Software Engineer",
        department="Engineering",
        manager_email="lead@betterup.co",
        start_date="2026-11-05",
        address=Address(street1="123 Market St", city="San Francisco", state="CA", postal_code="94105"),
        it_hardware_form_completed=False,
        background_check_status=BackgroundCheckStatus.PENDING,
        hardware_status=HardwareStatus.NOT_ORDERED,
        okta_status=OktaStatus.NOT_STAGED
    )


def test_gatekeeper_t_minus_5_days(base_hire):
    # Reference date is 2026-10-31 (5 days before 2026-11-05)
    gatekeeper = SLAGatekeeper(reference_date=date(2026, 10, 31))
    breaches = gatekeeper.evaluate_hire(base_hire)

    # Expect breaches for Hardware form (T-7) and Background check (T-7)
    gate_names = [b.gate_name for b in breaches]
    assert "IT Hardware Form" in gate_names
    assert "Background Check Clearance" in gate_names


def test_gatekeeper_all_clear(base_hire):
    # Update profile to cleared state
    base_hire.it_hardware_form_completed = True
    base_hire.background_check_status = BackgroundCheckStatus.CLEARED
    base_hire.hardware_status = HardwareStatus.SHIPPED
    base_hire.okta_status = OktaStatus.STAGED

    gatekeeper = SLAGatekeeper(reference_date=date(2026, 10, 31))
    breaches = gatekeeper.evaluate_hire(base_hire)
    assert len(breaches) == 0
