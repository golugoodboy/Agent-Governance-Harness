
from app.audit_inspector import inspect_audit
from app.audit_logger import AuditLogger


def test_inspector_reports_valid_audit_chain(tmp_path, capsys):
    db_path = tmp_path / "inspector.db"
    logger = AuditLogger(db_path)

    logger.append_event(
        "governance_decision",
        action="send_email",
        decision="ALLOW",
        risk_score=0.10,
        idempotency_key="inspector-test:decision",
    )

    exit_code = inspect_audit(str(db_path))
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Integrity: VALID" in output
    assert "governance_decision" in output
    assert "inspector-test:decision" in output
