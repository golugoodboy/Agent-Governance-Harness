
from datetime import datetime, timezone, timedelta

from app.approval_registry import ApprovalRegistry


def test_expired_approval_cannot_be_consumed(tmp_path):
    current_time = [
        datetime(2026, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    ]

    def fake_clock():
        return current_time[0]

    registry = ApprovalRegistry(
        db_path=tmp_path / "approval.db",
        ttl_seconds=900,
        now_provider=fake_clock,
    )

    approval_id = "approval-expiration-test"
    fingerprint = "test-fingerprint"

    created = registry.create_pending(
        approval_id=approval_id,
        audit_run_id="test-run-expiration",
        proposal_fingerprint=fingerprint,
        action="send_email",
    )

    assert created["status"] == "pending"

    # Simulate 16 minutes passing.
    current_time[0] += timedelta(minutes=16)

    result = registry.consume_approval(
        approval_id=approval_id,
        proposal_fingerprint=fingerprint,
        approved=True,
    )

    assert result["valid"] is False
    assert result["status"] == "expired"

    stored_approval = registry.get_approval(approval_id)

    assert stored_approval["status"] == "expired"


def test_approval_can_be_consumed_before_expiration(tmp_path):
    current_time = [
        datetime(2026, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    ]

    def fake_clock():
        return current_time[0]

    registry = ApprovalRegistry(
        db_path=tmp_path / "approval.db",
        ttl_seconds=900,
        now_provider=fake_clock,
    )

    approval_id = "approval-valid-test"
    fingerprint = "valid-fingerprint"

    created = registry.create_pending(
        approval_id=approval_id,
        audit_run_id="valid-run",
        proposal_fingerprint=fingerprint,
        action="send_email",
    )

    assert created["status"] == "pending"

    # Simulate 10 minutes passing.
    current_time[0] += timedelta(minutes=10)

    result = registry.consume_approval(
        approval_id=approval_id,
        proposal_fingerprint=fingerprint,
        approved=True,
    )

    assert result["valid"] is True
    assert result["status"] == "consumed"

    stored_approval = registry.get_approval(approval_id)
    assert stored_approval["status"] == "consumed"


def test_approval_expires_at_exact_ttl_boundary(tmp_path):
    current_time = [
        datetime(2026, 11, 6, 10, 0, 0, tzinfo=timezone.utc)
    ]

    def fake_clock():
        return current_time[0]

    registry = ApprovalRegistry(
        db_path=tmp_path / "approval.db",
        ttl_seconds=900,
        now_provider=fake_clock,
    )

    approval_id = "approval-boundary-test"
    fingerprint = "boundary-fingerprint"

    registry.create_pending(
        approval_id=approval_id,
        audit_run_id="boundary-run",
        proposal_fingerprint=fingerprint,
        action="send_email",
    )

    # Move exactly 900 seconds forward.
    current_time[0] += timedelta(seconds=900)

    result = registry.consume_approval(
        approval_id=approval_id,
        proposal_fingerprint=fingerprint,
        approved=True,
    )

    assert result["valid"] is False
    assert result["status"] == "expired"