
from unittest.mock import patch

from app.langgraph_agent.graph import build_graph
from app.schemas import ActionProposal


def test_followup_proposal_returns_to_governance():
    first_proposal = ActionProposal(
        action="search_web",
        reason="Initial search",
        confidence=0.95,
        risk_level="low",
        target="AI agents",
    )

    second_proposal = ActionProposal(
        action="search_web",
        reason="Follow-up search",
        confidence=0.95,
        risk_level="low",
        target="AI agent evaluation",
    )

    with (
        patch(
            "app.langgraph_agent.nodes.LLMProposalAgent.propose",
            return_value=first_proposal,
        ),
        patch(
            "app.langgraph_agent.nodes.Executor.execute",
            side_effect=[
                {
                    "status": "success",
                    "tool": "search_web",
                    "result": "Initial results",
                },
                {
                    "status": "success",
                    "tool": "search_web",
                    "result": "Follow-up results",
                },
            ],
        ),
        patch(
            "app.langgraph_agent.nodes.LLMProposalAgent.propose_followup",
            return_value={
                "decision": "continue",
                "proposal": second_proposal,
            },
        ) as followup,
    ):
        graph = build_graph()

        result = graph.invoke({
            "user_request": "Research AI agent evaluation",
            "status": "started",
            "audit_log": [],
            "step_count": 0,
            "max_steps": 2,
            "final_response": "",
        })

    assert followup.call_count == 1
    assert result["step_count"] == 2
    assert result["execution_result"]["result"] == "Follow-up results"
    assert result["status"] == "completed"


def test_blocked_action_does_not_trigger_followup():
    proposal = ActionProposal(
        action="delete_file",
        reason="Testing blocked action",
        confidence=0.99,
        risk_level="high",
        target="../../../../etc/passwd",
    )

    with (
        patch(
            "app.langgraph_agent.nodes.LLMProposalAgent.propose",
            return_value=proposal,
        ),
        patch(
            "app.langgraph_agent.nodes.Executor.execute",
            return_value={
                "status": "blocked",
                "reason": "Human review required",
            },
        ) as execute,
        patch(
            "app.langgraph_agent.nodes.LLMProposalAgent.propose_followup",
        ) as followup,
    ):
        graph = build_graph()

        result = graph.invoke({
            "user_request": "Delete a sensitive file",
            "status": "started",
            "audit_log": [],
            "step_count": 0,
            "max_steps": 3,
            "final_response": "",
        })

    assert execute.call_count == 1
    followup.assert_not_called()
    assert result["step_count"] == 1
    assert result["status"] == "blocked"