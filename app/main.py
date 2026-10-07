from app.agent import simulate_agent
from app.governor import Governor
from app.executor import Executor
from app.schemas import ActionProposal

def run(request : str):

    print("\n User request")
    print(request)

    #Agent Proposes action 
    proposal = simulate_agent(request)

    print("\n Agent Proposal")
    print(proposal)

    executor = Executor()
    result = executor.execute(proposal)

    print("\n Executor Result")
    print(result)

    return result

def run_test(name: str, proposal: ActionProposal):
    print(f"\n--- Running Test: {name} ---")
    print("Agent Proposal:", proposal)
    
    executor = Executor()
    result = executor.execute(proposal)
    
    print("\nExecutor Result:")
    print(result)
    return result

if __name__ == "__main__":
     run_test(
    "Valid Transfer",
    ActionProposal(
        action="transfer_money",
        reason="Testing valid transfer",
        confidence=0.95,
        risk_level="low",
        target="account_123",
        amount=5000
    )
)




