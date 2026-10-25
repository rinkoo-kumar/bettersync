import pytest
from src.core.reconciler import Reconciler
from src.models.events import EventType


@pytest.fixture
def reconciler():
    return Reconciler()


def test_offer_signed_propagation(reconciler):
    payload = {
        "hire_id": "HIRE-TEST-1",
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice.smith@betterup.co",
        "start_date": "2026-12-01",
        "role_title": "Product Manager",
        "department": "Product",
        "address": {
            "street1": "100 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country": "US"
        }
    }
    key = "offer_test_1"
    res = reconciler.ingest_event(EventType.OFFER_SIGNED, payload, idempotency_key=key)
    
    assert res["status"] == "SUCCESS"
    assert len(res["actions_taken"]) == 4

    # Verify Workday state
    wkd = reconciler.workday.get_by_hire_id("HIRE-TEST-1")
    assert wkd is not None
    assert wkd["start_date"] == "2026-12-01"

    # Verify Okta scheduled activation
    okta = reconciler.okta.get_by_hire_id("HIRE-TEST-1")
    assert okta is not None
    assert okta["scheduled_activation"] == "2026-12-01T06:00:00Z"

    # Verify ExpoIT order
    expo = reconciler.expoit.get_by_hire_id("HIRE-TEST-1")
    assert expo is not None
    assert expo["target_delivery_date"] == "2026-12-01"


def test_idempotent_replay(reconciler):
    payload = {
        "hire_id": "HIRE-TEST-IDEM",
        "start_date": "2026-12-01",
    }
    key = "idem_key_123"

    res1 = reconciler.ingest_event(EventType.START_DATE_UPDATED, payload, idempotency_key=key)
    assert res1["status"] == "SUCCESS"

    # Replay same event with identical idempotency key
    res2 = reconciler.ingest_event(EventType.START_DATE_UPDATED, payload, idempotency_key=key)
    assert res2["status"] == "ALREADY_PROCESSED"
    assert res2["idempotent"] is True


def test_off_cycle_worker_creation(reconciler):
    payload = {
        "hire_id": "HIRE-OFF-CYCLE-99",
        "first_name": "Bob",
        "last_name": "Vance",
        "email": "bob.vance@betterup.co",
        "start_date": "2026-12-15",
        "role_title": "Executive Advisor",
        "department": "Executive",
        "address": {"street1": "1 Scranton Plaza", "city": "Scranton", "state": "PA", "postal_code": "18503"}
    }
    res = reconciler.ingest_event(EventType.WORKER_CREATED_OFF_CYCLE, payload, idempotency_key="off_cycle_key_99")
    
    assert res["status"] == "SUCCESS"
    
    # Must exist in Workday with is_off_cycle flag
    wkd = reconciler.workday.get_by_hire_id("HIRE-OFF-CYCLE-99")
    assert wkd is not None
    assert wkd.get("is_off_cycle") is True

    # Must be staged in Okta
    okta = reconciler.okta.get_by_hire_id("HIRE-OFF-CYCLE-99")
    assert okta is not None
    assert okta["status"] == "STAGED"
