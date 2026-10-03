from app.agent import simulate_agent
from app.governor import Governor

def run(request : str):

    print("\n User request")
    print(request)

    #Agent Proposes action 
    proposal = simulate_agent(request)

    print("\n Agent Proposal")
    print(proposal)

    #harness Evaluated 
    governor = Governor()
    decision = governor.evaluate(proposal)

    print("\n Governor Decision")
    print(decision)

    return decision

if __name__ == "__main__":
    run("Please send an email to the customer")

    run("Please delete the important file")

