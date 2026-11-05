from app.schemas import ActionProposal
from app.executor import Executor
from app.langgraph_agent.llm_agent import LLMProposalAgent
from langgraph.types import interrupt
from app.schemas import Decision
from app.approval import proposal_fingerprint
from app.audit_logger import AuditLogger
import uuid
from app.approval_registry import ApprovalRegistry



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
    audit = AuditLogger()
    registry = ApprovalRegistry()

    preliminary = executor.governor.evaluate(proposal)
    decision = preliminary.decision
    fingerprint = proposal_fingerprint(proposal)

    audit_run_id = state.get("audit_run_id")
    approval_id = state.get("approval_id")

    if not audit_run_id:
        raise ValueError(
            "audit_run_id is required for idempotent audit logging"
        )

    def audit_key(event_type: str) -> str:
        return f"{audit_run_id}:{fingerprint}:{event_type}"

    def record_execution(result, approval_status):
        execution_status = result.get("status", "unknown")

        if execution_status == "success":
            event_type = "execution_completed"
        elif execution_status == "blocked":
            event_type = "execution_blocked"
        else:
            event_type = "execution_failed"

        audit.append_event(
            event_type,
            proposal_fingerprint=fingerprint,
            action=proposal.action,
            decision=getattr(
                result.get("decision", decision),
                "value",
                str(result.get("decision", decision)),
            ),
            risk_score=preliminary.risk_score,
            approval_status=approval_status,
            execution_status=execution_status,
            details={"source": "langgraph_governor_node"},
            idempotency_key=audit_key(event_type),
        )

    # Record hard denials without calling the executor again.
    if decision == Decision.BLOCK:
        audit.append_event(
            "governance_decision",
            proposal_fingerprint=fingerprint,
            action=proposal.action,
            decision="BLOCK",
            risk_score=preliminary.risk_score,
            approval_status="not_required",
            idempotency_key=audit_key("governance_decision"),
        )

        result = {
            "status": "blocked",
            "decision": Decision.BLOCK,
            "reason": preliminary.reason,
        }

        record_execution(result, "not_required")

        return {
            "governance_decision": "BLOCK",
            "execution_result": result,
            "step_count": state.get("step_count", 0) + 1,
            "status": "blocked",
            "approval_status": "not_required",
            "audit_log": [
                "Governance decision: BLOCK",
                "Execution status: blocked",
            ],
        }

    # Human review: do not write audit events before interrupt().
    # LangGraph reruns this node when the interrupt resumes.
    
    
    if decision == Decision.HUMAN_REVIEW:

        # Stable across LangGraph interrupt/resume.
        # A new workflow step gets a different approval ID.
        approval_id = str(
            uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{audit_run_id}:{state.get('step_count', 0)}",
    )
)

        # Retrieve an existing request, or create a new one.
        registered = registry.get_approval(approval_id)

        if registered is None:
            registered = registry.create_pending(
                approval_id=approval_id,
                audit_run_id=audit_run_id,
                proposal_fingerprint=fingerprint,
                action=proposal.action,
            )

        # Ensure the ID is still bound to the original request.
        same_request = (
            registered["audit_run_id"] == audit_run_id
            and registered["proposal_fingerprint"] == fingerprint
            and registered["action"] == proposal.action
        )

        if not same_request:
            registry.consume_approval(
                approval_id=approval_id,
                proposal_fingerprint=fingerprint,
                approved=True,
            )

            reason = (
                "Proposal fingerprint mismatch. Execution denied."
            )

            audit.append_event(
                "governance_decision",
                proposal_fingerprint=fingerprint,
                action=proposal.action,
                decision="HUMAN_REVIEW",
                risk_score=preliminary.risk_score,
                idempotency_key=audit_key("governance_decision"),
            )

            audit.append_event(
                "approval_invalidated",
                proposal_fingerprint=fingerprint,
                action=proposal.action,
                decision="HUMAN_REVIEW",
                risk_score=preliminary.risk_score,
                approval_status="invalidated",
                execution_status="blocked",
                details={"approval_id": approval_id},
                idempotency_key=audit_key("approval_invalidated"),
            )

            result = {
                "status": "blocked",
                "decision": Decision.HUMAN_REVIEW,
                "reason": reason,
            }

            record_execution(result, "invalidated")

            return {
                "governance_decision": "HUMAN_REVIEW",
                "execution_result": result,
                "step_count": state.get("step_count", 0) + 1,
                "status": "blocked",
                "approval_status": "invalidated",
                "approval_id": approval_id,
                "audit_log": [
                    "Governance decision: HUMAN_REVIEW",
                    reason,
                    "Execution status: blocked",
                ],
            }

        # Never allow a previously consumed approval to be reused.
        if registered["status"] != "pending":
            reason = (
                f"Approval cannot be reused: {registered['status']}"
            )

            return {
                "governance_decision": "HUMAN_REVIEW",
                "execution_result": {
                    "status": "blocked",
                    "decision": Decision.HUMAN_REVIEW,
                    "reason": reason,
                },
                "step_count": state.get("step_count", 0) + 1,
                "status": "blocked",
                "approval_status": registered["status"],
                "approval_id": approval_id,
                "audit_log": [reason, "Execution status: blocked"],
            }

        # Idempotency prevents a duplicate event on node resume.
        audit.append_event(
            "approval_requested",
            proposal_fingerprint=fingerprint,
            action=proposal.action,
            decision="HUMAN_REVIEW",
            risk_score=preliminary.risk_score,
            approval_status="pending",
            details={
                "source": "langgraph_governor_node",
                "audit_run_id": audit_run_id,
                "approval_id": approval_id,
            },
            idempotency_key=audit_key("approval_requested"),
        )

        approval = interrupt({
            "type": "approval_required",
            "approval_id": approval_id,
            "action": proposal.action,
            "target": proposal.target,
            "amount": proposal.amount,
            "reason": preliminary.reason,
            "risk_score": preliminary.risk_score,
            "fingerprint": fingerprint,
            "message": "Approve or reject this exact proposed action.",
        })

        # Append governance_decision upon resume for audit trail
        audit.append_event(
            "governance_decision",
            proposal_fingerprint=fingerprint,
            action=proposal.action,
            decision="HUMAN_REVIEW",
            risk_score=preliminary.risk_score,
            idempotency_key=audit_key("governance_decision"),
        )

        # Validate the complete response — approval_id is strictly required.
        valid_response = (
            isinstance(approval, dict)
            and approval.get("approval_id") == approval_id
            and approval.get("fingerprint") == fingerprint
            and type(approval.get("approved")) is bool
        )

        if not valid_response:
            # A malformed or mismatched response invalidates the request.
            registry.consume_approval(
                approval_id=approval_id,
                proposal_fingerprint = "invalid-response",
                approved = False,
                )

            approval_status = "invalidated"
            reason = "Invalid, stale, or replayed approval response."

            event_type = "approval_invalidated"

        else:
            # Atomically consume the approval or rejection.
            consumed = registry.consume_approval(
                approval_id=approval_id,
                proposal_fingerprint=fingerprint,
                approved=approval["approved"],
            )

            approval_status = consumed["status"]

            if not consumed["valid"]:
                reason = consumed["reason"]
                event_type = "approval_invalidated"

            elif approval_status == "rejected":
                reason = "Human approval rejected."
                event_type = "approval_rejected"

            elif approval_status == "consumed":
                reason = "Human approval accepted."
                event_type = "approval_approved"

            else:
                reason = "Approval could not be validated."
                event_type = "approval_invalidated"

        # Rejected, invalidated, and replayed requests cannot execute.
        if approval_status != "consumed":
            audit.append_event(
                event_type,
                proposal_fingerprint=fingerprint,
                action=proposal.action,
                decision="HUMAN_REVIEW",
                risk_score=preliminary.risk_score,
                approval_status=approval_status,
                execution_status="blocked",
                details={"approval_id": approval_id},
                idempotency_key=audit_key(event_type),
            )

            result = {
                "status": "blocked",
                "decision": Decision.HUMAN_REVIEW,
                "reason": reason,
            }

            record_execution(result, approval_status)

            return {
                "governance_decision": "HUMAN_REVIEW",
                "execution_result": result,
                "step_count": state.get("step_count", 0) + 1,
                "status": "blocked",
                "approval_status": approval_status,
                "approval_id": approval_id,
                "audit_log": [
                    reason,
                    "Execution status: blocked",
                ],
            }

        # Only a successfully consumed approval reaches execution.
        audit.append_event(
            "approval_approved",
            proposal_fingerprint=fingerprint,
            action=proposal.action,
            decision="HUMAN_REVIEW",
            risk_score=preliminary.risk_score,
            approval_status="approved",
            details={"approval_id": approval_id},
            idempotency_key=audit_key("approval_approved"),
        )

        result = executor.execute(
            proposal,
            human_approved=True,
        )

        final_decision = result.get("decision", Decision.ALLOW)
        final_decision = getattr(
            final_decision,
            "value",
            str(final_decision),
        )

        successful = result.get("status") == "success"

        final_approval_status = (
            "approved"
            if successful
            else "approved_but_not_executed"
        )

        record_execution(result, final_approval_status)

        return {
            "governance_decision": final_decision,
            "execution_result": result,
            "step_count": state.get("step_count", 0) + 1,
            "status": result.get("status", "unknown"),
            "approval_status": final_approval_status,
            "approval_id": approval_id,
            "audit_log": [
                "Human approval validated and consumed.",
                f"Post-approval governance decision: {final_decision}",
                f"Execution status: {result.get('status', 'unknown')}",
            ],
        }


    # Low-risk ALLOW path.
    audit.append_event(
        "governance_decision",
        proposal_fingerprint=fingerprint,
        action=proposal.action,
        decision="ALLOW",
        risk_score=preliminary.risk_score,
        approval_status="not_required",
        idempotency_key=audit_key("governance_decision")
    )

    result = executor.execute(proposal)

    final_decision = result.get("decision", decision)
    final_decision = getattr(
        final_decision, "value", str(final_decision)
    )

    record_execution(result, "not_required")

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
