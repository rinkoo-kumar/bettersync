import pytest
from src.core.audit_logger import AuditLogger


def test_audit_hash_chain_validity():
    logger = AuditLogger()
    r1 = logger.log("offer_signed", "HIRE-1", "webhook.ashby", {"name": "Bob"})
    r2 = logger.log("start_date_changed", "HIRE-1", "webhook.ashby", {"date": "2026-11-15"})
    r3 = logger.log("laptop_ordered", "HIRE-1", "worker.expoit", {"sku": "MBP-14"})

    assert r1.prev_hash == AuditLogger.GENESIS_HASH
    assert r2.prev_hash == r1.current_hash
    assert r3.prev_hash == r2.current_hash
    assert logger.verify_integrity() is True


def test_audit_tamper_detection():
    logger = AuditLogger()
    logger.log("offer_signed", "HIRE-1", "webhook.ashby", {"name": "Bob"})
    logger.log("start_date_changed", "HIRE-1", "webhook.ashby", {"date": "2026-11-15"})

    assert logger.verify_integrity() is True

    # Tamper with the first entry's diff maliciously
    logger._entries[0].diff["name"] = "MaliciousHacker"
    
    # Verification must fail!
    assert logger.verify_integrity() is False
