from app.langgraph_agent.graph import build_graph

def run_agent(user_request):

    graph = build_graph()

    print("\n" + "=" * 70)
    print("LANGGRAPH GOVERNANCE TEST")
    print("=" * 70)

    print(f"\nUser Request: {user_request}")

    result = graph.invoke({
    "user_request": user_request,
    "status": "started",
    "audit_log": [],
    "step_count": 0,
    "max_steps": 3,
    "final_response": ""
    })

    print("\n--- V0.6.5 Final State ---")
    print("Status:", result.get("status"))
    print("Governance:", result.get("governance_decision"))
    print("Proposal:", result.get("proposal"))
    print("Execution:", result.get("execution_result"))
    print("Response:", result.get("final_response"))

    print("\nAudit Log:")
    for event in result.get("audit_log", []):
        print("-", event)

    return result

if __name__ == "__main__":
    run_agent("Search for recent advances in AI agents")



    