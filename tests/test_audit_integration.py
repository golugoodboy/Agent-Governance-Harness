from app.audit_logger import AuditLogger
from app.schemas import ActionProposal, Decision, GovernorDecision
import app.langgraph_agent.nodes as nodes

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from app.approval import proposal_fingerprint
from app.langgraph_agent.states import AgentState

import pytest


def test_blocked_action_is_audited_without_execution(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "integration_audit.db"
    monkeypatch.setattr(
        nodes,
        "AuditLogger",
        lambda: AuditLogger(db_path),
    )

    execution_calls = []

    class FakeGovernor:
        def evaluate(self, proposal):
            return GovernorDecision(
                decision=Decision.BLOCK,
                reason="Tool is not authorized",
                risk_score=0.95,
            )

    class FakeExecutor:
        def __init__(self):
            self.governor = FakeGovernor()

        def execute(self, *args, **kwargs):
            execution_calls.append((args, kwargs))
            return {"status": "success"}

    monkeypatch.setattr(nodes, "Executor", FakeExecutor)

    proposal = ActionProposal(
        action="transfer_money",
        reason="Test denied action",
        confidence=0.95,
        risk_level="high",
        target="test-account",
        amount=1000,
    )

    result = nodes.governor_node({
        "proposal": proposal,
        "audit_run_id": "test-run-blocked",
        "status": "proposal_created",
        "audit_log": [],
        "step_count": 0,
    })

    assert result["status"] == "blocked"
    assert result["governance_decision"] == "BLOCK"
    assert execution_calls == []

    logger = AuditLogger(db_path)
    events = logger.list_events()

    assert [event["event_type"] for event in events] == [
        "governance_decision",
        "execution_blocked",
    ]

    assert all(
        event["decision"] == "BLOCK"
        for event in events
    )
    assert logger.verify_integrity()["valid"] is True



def build_audit_test_graph():
    builder = StateGraph(AgentState)
    builder.add_node("governor", nodes.governor_node)
    builder.add_edge(START, "governor")
    builder.add_edge("governor", END)
    return builder.compile(checkpointer=InMemorySaver())


def make_review_proposal():
    return ActionProposal(
        action="send_email",
        reason="Test human approval",
        confidence=0.95,
        risk_level="medium",
        target="test@example.com",
    )


def make_review_executor(execution_calls):
    class FakeGovernor:
        def evaluate(self, proposal):
            return GovernorDecision(
                decision=Decision.HUMAN_REVIEW,
                reason="Human approval required",
                risk_score=0.70,
            )

    class FakeExecutor:
        def __init__(self):
            self.governor = FakeGovernor()

        def execute(self, proposal, human_approved=False):
            execution_calls.append({
                "action": proposal.action,
                "human_approved": human_approved,
            })
            if human_approved:
                return {
                    "status": "success",
                    "decision": Decision.ALLOW,
                }
            return {
                "status": "blocked",
                "decision": Decision.HUMAN_REVIEW,
            }

    return FakeExecutor



def test_rejected_approval_is_audited(monkeypatch, tmp_path):
    db_path = tmp_path / "rejected_audit.db"
    monkeypatch.setattr(
        nodes, "AuditLogger", lambda: AuditLogger(db_path)
    )

    execution_calls = []
    monkeypatch.setattr(
        nodes, "Executor", make_review_executor(execution_calls)
    )

    graph = build_audit_test_graph()
    config = {"configurable": {"thread_id": "reject-test"}}
    proposal = make_review_proposal()

    interrupted = graph.invoke(
        {
            "proposal": proposal,
            "audit_run_id": "test-run-rejected",
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        },
        config=config,
    )

    assert "__interrupt__" in interrupted

    graph.invoke(
        Command(resume={
            "approved": False,
            "fingerprint": proposal_fingerprint(proposal),
        }),
        config=config,
    )

    logger = AuditLogger(db_path)
    events = logger.list_events()
    event_types = [event["event_type"] for event in events]

    assert event_types == [
    "approval_requested",
    "governance_decision",
    "approval_rejected",
    "execution_blocked",
    ]
    assert execution_calls == []
    assert logger.verify_integrity()["valid"] is True



def test_approved_execution_is_audited(monkeypatch, tmp_path):
    db_path = tmp_path / "approved_audit.db"
    monkeypatch.setattr(
        nodes, "AuditLogger", lambda: AuditLogger(db_path)
    )

    execution_calls = []
    monkeypatch.setattr(
        nodes, "Executor", make_review_executor(execution_calls)
    )

    graph = build_audit_test_graph()
    config = {"configurable": {"thread_id": "approve-test"}}
    proposal = make_review_proposal()
    fingerprint = proposal_fingerprint(proposal)

    interrupted = graph.invoke(
        {
            "proposal": proposal,
            "audit_run_id": "test-run-approved",
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        },
        config=config,
    )

    assert "__interrupt__" in interrupted

    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": fingerprint,
            }
        ),
        config=config,
    )

    logger = AuditLogger(db_path)
    events = logger.list_events()
    event_types = [event["event_type"] for event in events]

    assert result["status"] == "success"
    assert execution_calls == [{
        "action": "send_email",
        "human_approved": True,
    }]

    # Verify exact event ordering.
    assert event_types == [
        "approval_requested",
        "governance_decision",
        "approval_approved",
        "execution_completed",
    ]

    # Every event must reference the same proposal.
    assert all(
        event["proposal_fingerprint"] == fingerprint
        for event in events
    )

    # Every event must have a distinct idempotency key.
    keys = [event["idempotency_key"] for event in events]
    assert all(key is not None for key in keys)
    assert len(keys) == len(set(keys))

    # The audit hash chain must remain intact.
    assert logger.verify_integrity()["valid"] is True




def test_tampered_proposal_is_audited_and_blocked(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "tampered_audit.db"
    monkeypatch.setattr(
        nodes, "AuditLogger", lambda: AuditLogger(db_path)
    )

    execution_calls = []
    monkeypatch.setattr(
        nodes, "Executor", make_review_executor(execution_calls)
    )

    graph = build_audit_test_graph()
    config = {"configurable": {"thread_id": "tamper-test"}}
    proposal = make_review_proposal()

    interrupted = graph.invoke(
        {
            "proposal": proposal,
            "audit_run_id": "test-run-tamper",
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        },
        config=config,
    )

    assert "__interrupt__" in interrupted

    original_fingerprint = proposal_fingerprint(proposal)
    changed_proposal = proposal.model_copy(
        update={"target": "attacker@example.com"}
    )

    graph.update_state(
        config,
        {"proposal": changed_proposal},
    )

    result = graph.invoke(
        Command(resume={
            "approved": True,
            "fingerprint": original_fingerprint,
        }),
        config=config,
    )

    logger = AuditLogger(db_path)
    events = logger.list_events()
    event_types = [e["event_type"] for e in events]

    assert event_types == [
        "approval_requested",
        "governance_decision",
        "approval_invalidated",
        "execution_blocked",
    ]
    assert result["status"] == "blocked"
    assert execution_calls == []
    assert logger.verify_integrity()["valid"] is True



def test_audit_failure_prevents_execution(monkeypatch):
    execution_calls = []

    class FakeGovernor:
        def evaluate(self, proposal):
            return GovernorDecision(
                decision=Decision.ALLOW,
                reason="Authorized",
                risk_score=0.10,
            )

    class FakeExecutor:
        def __init__(self):
            self.governor = FakeGovernor()

        def execute(self, *args, **kwargs):
            execution_calls.append((args, kwargs))
            return {"status": "success"}

    class BrokenAuditLogger:
        def __init__(self):
            pass

        def append_event(self, *args, **kwargs):
            raise OSError("Simulated audit database failure")

    monkeypatch.setattr(nodes, "Executor", FakeExecutor)
    monkeypatch.setattr(nodes, "AuditLogger", BrokenAuditLogger)

    proposal = ActionProposal(
        action="send_email",
        reason="Test audit failure",
        confidence=0.95,
        risk_level="low",
        target="test@example.com",
    )

    try:
        nodes.governor_node({
            "proposal": proposal,
            "audit_run_id": "test-run-failure",
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        })
    except OSError as exc:
        assert "audit database failure" in str(exc)
    else:
        raise AssertionError("Expected audit failure to stop execution")

    assert execution_calls == []



def test_missing_audit_run_id_fails_closed(monkeypatch):
    execution_calls = []

    class FakeGovernor:
        def evaluate(self, proposal):
            return GovernorDecision(
                decision=Decision.ALLOW,
                reason="Authorized",
                risk_score=0.10,
            )

    class FakeExecutor:
        def __init__(self):
            self.governor = FakeGovernor()

        def execute(self, *args, **kwargs):
            execution_calls.append((args, kwargs))
            return {"status": "success"}

    monkeypatch.setattr(nodes, "Executor", FakeExecutor)

    proposal = ActionProposal(
        action="send_email",
        reason="Test missing run ID",
        confidence=0.95,
        risk_level="low",
        target="test@example.com",
    )

    with pytest.raises(ValueError, match="audit_run_id is required"):
        nodes.governor_node({
            "proposal": proposal,
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        })

    assert execution_calls == []
