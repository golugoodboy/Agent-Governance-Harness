
import sqlite3

from app.audit_logger import AuditLogger


def test_audit_event_is_persisted(tmp_path):
    db_path = tmp_path / "audit.db"

    logger = AuditLogger(db_path)
    event = logger.append_event(
        "governance_decision",
        action="send_email",
        decision="HUMAN_REVIEW",
        risk_score=0.70,
        approval_status="pending",
        details={"reason": "Human approval required"},
    )

    events = logger.list_events()

    assert len(events) == 1
    assert events[0]["event_id"] == event["event_id"]
    assert events[0]["action"] == "send_email"
    assert events[0]["details"]["reason"] == "Human approval required"

    # Reopen the same database to verify persistence.
    reopened_logger = AuditLogger(db_path)
    assert len(reopened_logger.list_events()) == 1


def test_hash_chain_is_valid(tmp_path):
    logger = AuditLogger(tmp_path / "audit.db")

    logger.append_event(
        "proposal_created",
        action="search_web",
    )
    logger.append_event(
        "governance_decision",
        action="search_web",
        decision="ALLOW",
    )
    logger.append_event(
        "execution_completed",
        action="search_web",
        execution_status="success",
    )

    result = logger.verify_integrity()

    assert result["valid"] is True
    assert result["events_checked"] == 3


def test_modified_event_is_detected(tmp_path):
    db_path = tmp_path / "audit.db"
    logger = AuditLogger(db_path)

    logger.append_event(
        "governance_decision",
        action="send_email",
        decision="BLOCK",
    )

    # Simulate someone modifying a recorded decision directly.
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET decision = ? WHERE id = ?",
            ("ALLOW", 1),
        )

    result = logger.verify_integrity()

    assert result["valid"] is False
    assert result["reason"] == "Event hash mismatch"
