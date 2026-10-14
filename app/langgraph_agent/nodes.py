from app.schemas import ActionProposal
from app.executor import Executor
from app.langgraph_agent.llm_agent import LLMProposalAgent



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


def route_after_agent(state):
    if state.get("proposal") is not None:
        return "governor"
    return "stop"




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



def governor_node(state):

    proposal = state["proposal"]

    executor = Executor()

    result = executor.execute(proposal)

    decision = result.get("decision")

    if decision is not None:
        decision = getattr(decision, "value", str(decision))
    
    if decision is None: 
        decision = ("ALLOW" if result.get("status") == "success" else "UNKNOWN")
    

    
    return {
        "governance_decision": decision,
        "execution_result" : result,
        "status" : ("Completed" if result.get("status") == "success" else result.get("status", "Unknown")),
        "audit_log" : [f"Governance Decided {decision}", f"Execution Status : {result.get("status")}"]
    }

    


