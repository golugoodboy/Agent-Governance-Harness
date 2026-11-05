from types import SimpleNamespace

from langgraph.types import Command

import app.langgraph_agent.nodes as nodes
from app.langgraph_agent.graph import build_graph

from app.approval_registry import ApprovalRegistry
from app.audit_logger import AuditLogger
from app.schemas import ActionProposal, Decision, GovernorDecision


def test_wrong_approval_id_is_rejected(
    monkeypatch,
    tmp_path,
):
    proposal = ActionProposal(
        action="send_email",
        reason="Test approval ID validation",
        confidence=0.95,
        risk_level="high",
        target="test@example.com",
    )

    execution_calls = []

    # Mock LLM proposal generation.
    fake_agent = SimpleNamespace(
        propose=lambda request: proposal
    )

    monkeypatch.setattr(
        nodes,
        "LLMProposalAgent",
        lambda: fake_agent,
    )

    # Mock executor while retaining real governance-node logic.
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

    monkeypatch.setattr(
        nodes,
        "Executor",
        FakeExecutor,
    )

    # Isolate databases for this test.
    registry_path = tmp_path / "approval.db"
    audit_path = tmp_path / "audit.db"

    monkeypatch.setattr(
        nodes,
        "ApprovalRegistry",
        lambda: ApprovalRegistry(registry_path),
    )

    monkeypatch.setattr(
        nodes,
        "AuditLogger",
        lambda: AuditLogger(audit_path),
    )

    graph = build_graph()

    config = {
        "configurable": {
            "thread_id": "wrong-approval-id-test",
        }
    }

    initial_state = {
        "user_request": "Send a test email",
        "audit_run_id": "test-run-wrong-id",
        "status": "started",
        "audit_log": [],
        "step_count": 0,
        "max_steps": 3,
        "final_response": "",
    }

    # Start workflow. It should pause for approval.
    paused = graph.invoke(
        initial_state,
        config=config,
    )

    interrupts = paused.get("__interrupt__", [])

    assert interrupts, "Graph did not pause for approval."

    approval_details = interrupts[0].value

    expected_approval_id = approval_details["approval_id"]
    fingerprint = approval_details["fingerprint"]

    # Resume with an incorrect approval ID.
    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": fingerprint,
                "approval_id": "incorrect-approval-id",
            }
        ),
        config=config,
    )

    assert result["status"] == "blocked"
    assert result["approval_status"] == "invalidated"

    # The executor must never run.
    assert execution_calls == []

    # Verify the registry invalidated the original request.
    registry = ApprovalRegistry(registry_path)

    registered = registry.get_approval(
        expected_approval_id
    )

    assert registered["status"] == "invalidated"


def test_missing_approval_id_is_rejected(monkeypatch, tmp_path):
    proposal = ActionProposal(
        action="send_email",
        reason="Test missing approval ID",
        confidence=0.95,
        risk_level="high",
        target="test@example.com",
    )

    execution_calls = []

    fake_agent = SimpleNamespace(
        propose=lambda request: proposal
    )
    monkeypatch.setattr(nodes, "LLMProposalAgent", lambda: fake_agent)

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

    registry_path = tmp_path / "approval.db"
    audit_path = tmp_path / "audit.db"

    monkeypatch.setattr(
        nodes,
        "ApprovalRegistry",
        lambda: ApprovalRegistry(registry_path),
    )
    monkeypatch.setattr(
        nodes,
        "AuditLogger",
        lambda: AuditLogger(audit_path),
    )

    graph = build_graph()

    config = {
        "configurable": {
            "thread_id": "missing-approval-id-test"
        }
    }

    initial_state = {
        "user_request": "Send a test email",
        "audit_run_id": "test-run-missing-id",
        "status": "started",
        "audit_log": [],
        "step_count": 0,
        "max_steps": 3,
        "final_response": "",
    }

    paused = graph.invoke(initial_state, config=config)

    interrupts = paused.get("__interrupt__", [])
    assert interrupts, "Graph did not pause for approval."

    approval_details = interrupts[0].value
    fingerprint = approval_details["fingerprint"]

    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": fingerprint,
            }
        ),
        config=config,
    )

    assert result["status"] == "blocked"
    assert result["approval_status"] == "invalidated"
    assert execution_calls == []

    
def test_consumed_approval_cannot_be_replayed_through_graph(
    monkeypatch, tmp_path
):
    proposal = ActionProposal(
        action="send_email",
        reason="Test approval replay protection",
        confidence=0.95,
        risk_level="high",
        target="test@example.com",
    )

    execution_calls = []

    fake_agent = SimpleNamespace(
        propose=lambda request: proposal
    )
    monkeypatch.setattr(
        nodes, "LLMProposalAgent", lambda: fake_agent
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

    registry_path = tmp_path / "approval.db"
    audit_path = tmp_path / "audit.db"

    monkeypatch.setattr(
        nodes,
        "ApprovalRegistry",
        lambda: ApprovalRegistry(registry_path),
    )
    monkeypatch.setattr(
        nodes,
        "AuditLogger",
        lambda: AuditLogger(audit_path),
    )

    graph = build_graph()

    audit_run_id = "test-run-approval-replay"

    def make_initial_state():
        return {
            "user_request": "Send a test email",
            "audit_run_id": audit_run_id,
            "status": "started",
            "audit_log": [],
            "step_count": 0,
            "max_steps": 3,
            "final_response": "",
        }

    # FIRST SESSION: Request and approve the action.
        first_config = {
        "configurable": {
            "thread_id": "approval-replay-first-session"
        }
    }

        paused = graph.invoke(
        make_initial_state(),
        config=first_config,
    )

        interrupts = paused.get("__interrupt__", [])
        assert interrupts, "Graph did not pause for approval."

        approval_details = interrupts[0].value

        approval_id = approval_details["approval_id"]
        fingerprint = approval_details["fingerprint"]

        approved_result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": fingerprint,
                "approval_id": approval_id,
            }
        ),
        config=first_config,
    )

        assert len(execution_calls) == 1

        registry = ApprovalRegistry(registry_path)
        registered = registry.get_approval(approval_id)

        assert registered["status"] == "consumed"

    # SECOND SESSION: Attempt to reuse the same approval request.
        second_config = {
        "configurable": {
            "thread_id": "approval-replay-second-session"
        }
    }

        replay_result = graph.invoke(
        make_initial_state(),
        config=second_config,
    )

    # The consumed approval must not authorize another execution.
        assert replay_result["status"] == "blocked"
        assert replay_result["approval_status"] == "consumed"

    # Execution must have happened exactly once.
        assert len(execution_calls) == 1
