from app.agent import simulate_agent
from app.governor import Governor
from app.executor import Executor

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

if __name__ == "__main__":
    run("send email")
    run("delete file")
    run("transfer money")
    run("Unknown tool")




