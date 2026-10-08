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
        "status" : "Proposal Created"}


def governor_node(state):

    proposal = state["proposal"]

    executor = Executor()

    result = executor.execute(proposal)

    print("\n Executor Result: ")
    print(result)

    return {
        "execution_result" : result,
        "status" : result.get("status", "Unknown")
    }

