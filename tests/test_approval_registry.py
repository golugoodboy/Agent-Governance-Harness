
import pytest

from app.approval_registry import ApprovalRegistry


@pytest.fixture
def registry(tmp_path):
    db_path = tmp_path / "approval_test.db"
    return ApprovalRegistry(str(db_path))


def test_create_pending_approval(registry):
    result = registry.create_pending(
        approval_id="approval-001",
        audit_run_id="run-001",
        proposal_fingerprint="fingerprint-abc",
        action="send_email",
    )

    assert result["status"] == "pending"


def test_approval_can_only_be_consumed_once(registry):
    registry.create_pending(
        "approval-002",
        "run-002",
        "fingerprint-abc",
        "send_email",
    )

    first = registry.consume_approval(
        "approval-002",
        "fingerprint-abc",
        True,
    )

    assert first["valid"] is True
    assert first["status"] == "consumed"

    with pytest.raises(ValueError, match="no longer pending"):
        registry.consume_approval(
            "approval-002",
            "fingerprint-abc",
            True,
        )


def test_fingerprint_mismatch_invalidates_approval(registry):
    registry.create_pending(
        "approval-003",
        "run-003",
        "original-fingerprint",
        "send_email",
    )

    result = registry.consume_approval(
        "approval-003",
        "tampered-fingerprint",
        True,
    )

    assert result["valid"] is False
    assert result["status"] == "invalidated"


def test_rejected_approval_cannot_be_reused(registry):
    registry.create_pending(
        "approval-004",
        "run-004",
        "fingerprint-abc",
        "send_email",
    )

    result = registry.consume_approval(
        "approval-004",
        "fingerprint-abc",
        False,
    )

    assert result["status"] == "rejected"

    with pytest.raises(ValueError):
        registry.consume_approval(
            "approval-004",
            "fingerprint-abc",
            True,
        )


def test_approval_id_cannot_be_reused_for_another_request(registry):
    registry.create_pending(
        "approval-005",
        "run-005",
        "fingerprint-abc",
        "send_email",
    )

    with pytest.raises(ValueError, match="another request"):
        registry.create_pending(
            "approval-005",
            "run-005",
            "different-fingerprint",
            "send_email",
        )
