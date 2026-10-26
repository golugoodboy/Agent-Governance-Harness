
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.schemas import ActionProposal, Decision, GovernorDecision
from app.langgraph_agent.states import AgentState
import app.langgraph_agent.nodes as nodes


def build_test_graph(monkeypatch, execution_calls):
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
            execution_calls.append(
                {
                    "action": proposal.action,
                    "human_approved": human_approved,
                }
            )

            if not human_approved:
                return {
                    "status": "blocked",
                    "decision": Decision.HUMAN_REVIEW,
                    "reason": "Approval required",
                }

            return {
                "status": "success",
                "decision": Decision.ALLOW,
                "result": "Mock execution successful",
            }

    monkeypatch.setattr(nodes, "Executor", FakeExecutor)

    workflow = StateGraph(AgentState)
    workflow.add_node("governor", nodes.governor_node)
    workflow.add_edge(START, "governor")
    workflow.add_edge("governor", END)

    return workflow.compile(checkpointer=InMemorySaver())


import uuid

def make_initial_state(run_id: str | None = None):
    return {
        "user_request": "Send a test email",
        "audit_run_id": run_id or f"test-human-approval-{uuid.uuid4()}",
        "proposal": ActionProposal(
            action="send_email",
            reason="Test approval workflow",
            confidence=0.95,
            risk_level="medium",
            target="test@example.com",
        ),
        "status": "proposal_created",
        "audit_log": [],
        "step_count": 0,
        "max_steps": 3,
        "final_response": "",
    }


def test_rejected_action_is_not_executed(monkeypatch):
    execution_calls = []
    graph = build_test_graph(monkeypatch, execution_calls)
    config = {"configurable": {"thread_id": "approval-reject-test"}}

    result = graph.invoke(make_initial_state(), config=config)

    # The graph must pause and ask for approval.
    assert result.get("__interrupt__")
    assert execution_calls == []
    details = result["__interrupt__"][0].value

    # Reject the pending action.
    result = graph.invoke(
        Command(
            resume={
                "approved": False,
                "fingerprint": details["fingerprint"],
            }
        ),
        config=config,
    )

    assert result["status"] == "blocked"
    assert result["approval_status"] == "rejected"
    assert execution_calls == []


def test_approved_action_is_executed(monkeypatch):
    execution_calls = []
    graph = build_test_graph(monkeypatch, execution_calls)
    config = {"configurable": {"thread_id": "approval-accept-test"}}

    result = graph.invoke(make_initial_state(), config=config)

    # No execution should happen before approval.
    assert result.get("__interrupt__")
    assert execution_calls == []
    details = result["__interrupt__"][0].value

    # Approve the pending action.
    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": details["fingerprint"],
            }
        ),
        config=config,
    )

    assert result["status"] == "success"
    assert result["approval_status"] == "approved"
    assert execution_calls == [
        {
            "action": "send_email",
            "human_approved": True,
        }
    ]



def test_changed_proposal_invalidates_approval(monkeypatch):
    execution_calls = []
    graph = build_test_graph(monkeypatch, execution_calls)
    config = {"configurable": {"thread_id": "approval-tamper-test"}}

    result = graph.invoke(make_initial_state(), config=config)

    assert result.get("__interrupt__")
    details = result["__interrupt__"][0].value

    # Change the target while approval is pending.
    changed_proposal = make_initial_state()["proposal"].model_copy(
        update={"target": "attacker@example.com"}
    )

    graph.update_state(
        config,
        {"proposal": changed_proposal},
    )

    # Attempt to resume using the fingerprint from the original proposal.
    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "fingerprint": details["fingerprint"],
            }
        ),
        config=config,
    )

    assert result["status"] == "blocked"
    assert result["approval_status"] == "invalidated"
    assert "fingerprint mismatch" in result["execution_result"]["reason"].lower()
    assert execution_calls == []
