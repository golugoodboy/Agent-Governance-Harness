from app.schemas import ActionProposal
from app.executor import Executor

def agent_node(state):

    user_request = state["user_request"]

    if "email" in user_request.lower():
        proposal = ActionProposal(
            action="send_email",
            reason="User requested to send an email",
            confidence=0.95,
            risk_level="low",
            target="customer@gmail.com"
        )
        
    elif "search" in user_request.lower():
        proposal = ActionProposal(
            action="search_web",
            reason="User requested to search for something",
            confidence=0.95,
            risk_level="low",
            target="latest AI News"
        )

    else:
        proposal = ActionProposal(
            action="search_web",
            reason="Default search action.",
            confidence=0.95,
            risk_level="low",
            target = user_request
        )
        

    print("\n Langgraph Proposal : ")
    print(proposal)

    return {
        "proposal": proposal,
        "status" : "Proposal Created",
        "audit_log" : [f"Agent Proposed Action {proposal.action}"]}



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

    


