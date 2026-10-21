from app.audit_logger import AuditLogger
from app.schemas import ActionProposal, Decision, GovernorDecision
import app.langgraph_agent.nodes as nodes

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from app.approval import proposal_fingerprint
from app.langgraph_agent.states import AgentState


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
    event_types = [e["event_type"] for e in logger.list_events()]

    assert "governance_decision" in event_types
    assert "approval_rejected" in event_types
    assert "execution_blocked" in event_types
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

    interrupted = graph.invoke(
        {
            "proposal": proposal,
            "status": "proposal_created",
            "audit_log": [],
            "step_count": 0,
        },
        config=config,
    )

    assert "__interrupt__" in interrupted

    result = graph.invoke(
        Command(resume={
            "approved": True,
            "fingerprint": proposal_fingerprint(proposal),
        }),
        config=config,
    )

    logger = AuditLogger(db_path)
    event_types = [e["event_type"] for e in logger.list_events()]

    assert result["status"] == "success"
    assert execution_calls == [{
        "action": "send_email",
        "human_approved": True,
    }]
    assert "approval_approved" in event_types
    assert "execution_completed" in event_types
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

    assert result["status"] == "blocked"
    assert execution_calls == []
    assert "approval_invalidated" in event_types
    assert "execution_blocked" in event_types
    assert logger.verify_integrity()["valid"] is True
