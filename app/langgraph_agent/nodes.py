from app.schemas import ActionProposal
from app.executor import Executor
from app.langgraph_agent.llm_agent import LLMProposalAgent
from langgraph.types import interrupt
from app.schemas import Decision
from app.approval import proposal_fingerprint


# LLM Node that generates a proposal
def agent_node(state):
    try:
        user_request = state["user_request"]

        agent = LLMProposalAgent()

        proposal = agent.propose(user_request)

        print("\n[LANGGRAPH] LLM-generated proposal:")
        print(proposal)

        return {
        "proposal": proposal,
        "status": "proposal_created",
        "audit_log": [
            f"LLM proposed action: {proposal.action}"
        ],
    }

    except Exception as e:
        print(f"[LANGGRAPH] Proposal generation failed: {e}")

        return {
            "proposal": None,
            "status": "proposal_error",
            "audit_log": [
                "Proposal generation failed; execution was not attempted."
            ],
        }

# Routes to Governance if proposal exists and status is proposal_created otherwise stops
def route_after_agent(state):
    if state.get("status") != "proposal_created":
        return "stop"

    if state.get("proposal") is None:
        return "stop"

    return "governance"




#def agent_node(state):

#    user_request = state["user_request"]

#    if "email" in user_request.lower():
#        proposal = ActionProposal(
#            action="send_email",
#            reason="User requested to send an email",
#            confidence=0.95,
#            risk_level="low",
#            target="customer@gmail.com"
#        )
        
#    elif "search" in user_request.lower():
#        proposal = ActionProposal(
#            action="search_web",
#            reason="User requested to search for something",
#            confidence=0.95,
#            risk_level="low",
#            target="latest AI News"
#        )

#    else:
#        proposal = ActionProposal(
#            action="search_web",
#            reason="Default search action.",
#            confidence=0.95,
#            risk_level="low",
#            target = user_request
#        )
        

#    print("\n Langgraph Proposal : ")
#    print(proposal)

#    return {
#        "proposal": proposal,
#        "status" : "Proposal Created",
#        "audit_log" : [f"Agent Proposed Action {proposal.action}"]}


#Governance Node that executes the proposal and updates the state.
def governor_node(state):
    proposal = state["proposal"]
    executor = Executor() 

    preliminary = executor.governor.evaluate(proposal)
    decision = preliminary.decision

    if decision == Decision.BLOCK:
        result = executor.execute(proposal)

        return {
            "governance_decision": "BLOCK",
            "execution_result": result,
            "step_count": state.get("step_count", 0) + 1,
            "status": result.get("status", "blocked"),
            "approval_status": "not_required",
            "audit_log": [
                "Governance decision: BLOCK",
                "Execution status: blocked",
                "Hard denial cannot be overridden by approval.",
            ],
        }
     
    
    if decision == Decision.HUMAN_REVIEW:
        fingerprint = proposal_fingerprint(proposal)

        approval = interrupt({
            "type": "approval_required",
            "action": proposal.action,
            "target": proposal.target,
            "amount": proposal.amount,
            "reason": preliminary.reason,
            "risk_score": preliminary.risk_score,
            "fingerprint": fingerprint,
            "message": "Approve or reject this exact proposed action.",
        })

        # Recalculate the fingerprint after resuming.
        current_fingerprint = proposal_fingerprint(proposal)

        approved = (
            isinstance(approval, dict)
            and approval.get("approved") is True
            and approval.get("fingerprint") == current_fingerprint
        )

        if not approved:
            fingerprint_matches = (
                isinstance(approval, dict)
                and approval.get("fingerprint") == current_fingerprint
            )

            reason = (
                "Approval rejected or invalid."
                if not isinstance(approval, dict)
                or approval.get("approved") is not True
                else "Proposal fingerprint mismatch. Execution denied."
            )

            result = {
                "status": "blocked",
                "reason": reason,
            }

            return {
            "governance_decision": "HUMAN_REVIEW",
            "execution_result": result,
            "step_count": state.get("step_count", 0) + 1,
            "status": "blocked",
            "approval_status": (
                "rejected" if fingerprint_matches else "invalidated"
            ),
            "audit_log": [
                "Governance decision: HUMAN_REVIEW",
                reason,
                "Execution status: blocked",
            ],
        }

        # Executor runs its governance checks again after approval.
        result = executor.execute(proposal, human_approved=True)

        final_decision = result.get("decision", Decision.ALLOW)
        final_decision = getattr(final_decision, "value", str(final_decision))
        successful = result.get("status") == "success"

        return {
            "governance_decision": final_decision,
            "execution_result": result,
            "step_count": state.get("step_count", 0) + 1,
            "status": result.get("status", "unknown"),
            "approval_status": (
                "approved" if successful else "approved_but_not_executed"
            ),
            "audit_log": [
                "Human approval matched the pending proposal fingerprint.",
                f"Post-approval governance decision: {final_decision}",
                f"Execution status: {result.get('status', 'unknown')}",
            ],
        }


    result = executor.execute(proposal)
    final_decision = result.get("decision", decision)
    final_decision = getattr(
        final_decision, "value", str(final_decision)
    )

    return {
        "governance_decision": final_decision,
        "execution_result": result,
        "step_count": state.get("step_count", 0) + 1,
        "status": result.get("status", "unknown"),
        "approval_status": "not_required",
        "audit_log": [
            f"Governance decision: {final_decision}",
            f"Execution status: {result.get('status', 'unknown')}",
        ],
    }


    
#Result node, that gives the final result to the user
def result_node(state):

    result = state.get("execution_result") or {}

    status = result.get("status", "unknown")

    if status == "success":
        final_response = (
            "The requested action completed successfully. "
            f"Result: {result.get('result', 'No details returned.')}"
        )
    elif status == "blocked":
        final_response = (
            "The action was not executed because the governance "
            f"harness blocked it: {result.get('reason', 'No reason provided.')}"
        )
    else:
        final_response = (
            "The action did not complete successfully. "
            f"Status: {status}. "
            f"Details: {result.get('reason', result.get('error', 'Unknown error'))}"
        )

    return {
        "final_response": final_response,
        "status": "completed" if status == "success" else status,
        "audit_log": [
            f"Result processed: {status}"
        ],
    }

def followup_node(state):
    result = state.get("execution_result") or {}
    proposal = state.get("proposal")
    count = state.get("step_count", 0)
    maximum = state.get("max_steps", 3)

    if result.get("status") != "success":
        return {
            "next_step" : "finish",
            "final_response" : ("The workflow stopped because the action did not "
                f"complete successfully: {result.get('reason', result.get('error', result.get('status')))}"),
            "audit_log" : ["Follow-up stopped after unsuccessful execution."]
        }

    if count >= maximum:
        return {
            "next_step": "finish",
            "final_response": (
                "The workflow reached its maximum number of proposals. "
                f"Last result: {result.get('result', 'Success')}"
            ),
            "audit_log": ["Maximum proposal count reached."],
        }

    try: 
        agent = LLMProposalAgent()

        outcome = agent.propose_followup(
            user_request=state["user_request"],
            previous_proposal=proposal,
            execution_result=result,
            step_count=count,
            max_steps=maximum,
        )

        if outcome["decision"] == "finish":
            return {
                "next_step": "finish",
                "final_response": outcome["final_response"],
                "audit_log": ["LLM decided the workflow is complete."],
            }

        next_proposal = outcome["proposal"]

        return {
            "proposal": next_proposal,
            "next_step": "governance",
            "status": "proposal_created",
            "audit_log": [
                f"LLM proposed follow-up action: {next_proposal.action}"
            ],
        }

    except Exception as exc:
        return {
            "next_step": "finish",
            "status": "followup_error",
            "final_response": (
                "The workflow stopped because follow-up planning failed. "
                "No additional action was executed."
            ),
            "audit_log": [
                f"Follow-up planning failed: {type(exc).__name__}"
            ],
        }

def route_after_followup(state):
    if (
        state.get("next_step") == "governance"
        and state.get("proposal") is not None
        and state.get("step_count", 0) < state.get("max_steps", 3)
    ):
        return "governance"

    return "result"
