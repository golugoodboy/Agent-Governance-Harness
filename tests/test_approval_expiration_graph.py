
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from langgraph.types import Command

import app.langgraph_agent.nodes as nodes
from app.langgraph_agent.graph import build_graph

from app.approval_registry import ApprovalRegistry
from app.audit_logger import AuditLogger
from app.schemas import ActionProposal, Decision, GovernorDecision


def test_expired_approval_cannot_execute_through_graph(
    monkeypatch,
    tmp_path,
):
    # A controllable clock lets us simulate expiration.
    clock = {
        "now": datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    }

    def fake_now():
        return clock["now"]

    proposal = ActionProposal(
        action="send_email",
        reason="Test approval expiration",
        confidence=0.95,
        risk_level="high",
        target="test@example.com",
    )

    execution_calls = []

    fake_agent = SimpleNamespace(
        propose=lambda request: proposal
    )

    monkeypatch.setattr(
        nodes,
        "LLMProposalAgent",
        lambda: fake_agent,
    )

    class FakeExecutor:
        def __init__(self):
            self.governor = SimpleNamespace(
                evaluate=lambda proposal: GovernorDecision(
                    decision=Decision.HUMAN_REVIEW,
                    reason="Human approval required",
                    risk_score=0.8,
                )
            )

        def execute(self, proposal, human_approved=False):
            execution_calls.append(proposal)

            return {
                "status": "success",
                "decision": Decision.ALLOW,
                "result": "Simulated execution",
            }

    monkeypatch.setattr(nodes, "Executor", FakeExecutor)

    registry_path = tmp_path / "approval_expiration.db"
    audit_path = tmp_path / "audit_expiration.db"

    def registry_factory():
        return ApprovalRegistry(
            db_path=registry_path,
            ttl_seconds=900,
            now_provider=fake_now,
        )

    monkeypatch.setattr(
        nodes,
        "ApprovalRegistry",
        registry_factory,
    )

    monkeypatch.setattr(
        nodes,
        "AuditLogger",
        lambda: AuditLogger(audit_path),
    )

    graph = build_graph()

    config = {
        "configurable": {
            "thread_id": "approval-expiration-test",
        }
    }

    initial_state = {
        "user_request": "Send a test email",
        "audit_run_id": "test-run-expiration",
        "status": "started",
        "audit_log": [],
        "step_count": 0,
        "max_steps": 3,
        "final_response": "",
    }

    # Start the workflow and capture the approval request.
    paused = graph.invoke(
        initial_state,
        config=config,
    )

    interrupts = paused.get("__interrupt__", [])

    assert interrupts, "Graph did not pause for approval."

    approval_details = interrupts[0].value

    approval_id = approval_details["approval_id"]
    fingerprint = approval_details["fingerprint"]

    # Advance time beyond the 15-minute TTL.
    clock["now"] += timedelta(minutes=16)

    # Resume with an otherwise valid approval response.
    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": fingerprint,
                "approval_id": approval_id,
            }
        ),
        config=config,
    )

    # Expired approval must be blocked.
    assert result["status"] == "blocked"
    assert result["approval_status"] == "expired"

    # No execution must take place.
    assert execution_calls == []

    # Verify persistent registry status.
    registry = registry_factory()

    registered = registry.get_approval(approval_id)

    assert registered["status"] == "expired"

    # Verify the expiration audit event.
    audit = AuditLogger(audit_path)
    events = audit.list_events()

    expired_events = [
        event
        for event in events
        if event["event_type"] == "approval_expired"
    ]

    assert expired_events
