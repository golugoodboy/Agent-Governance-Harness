
from langgraph.types import Command

from app.langgraph_agent.graph import build_graph


def run_agent(user_request):

    graph = build_graph()

    config = {
        "configurable": {
            "thread_id": "governance-session-001"
        }
    }

    print("\n" + "=" * 70)
    print("LANGGRAPH GOVERNANCE TEST - V0.7")
    print("=" * 70)
    print(f"\nUser Request: {user_request}")

    result = graph.invoke(
        {
            "user_request": user_request,
            "status": "started",
            "audit_log": [],
            "step_count": 0,
            "max_steps": 3,
            "final_response": "",
        },
        config=config,
    )

    # Handle any human approval interrupts.
    while result.get("__interrupt__"):

        interrupts = result["__interrupt__"]

        for interrupt_event in interrupts:
            details = interrupt_event.value

            print("\n" + "=" * 70)
            print("HUMAN APPROVAL REQUIRED")
            print("=" * 70)

            print("Action:", details.get("action"))
            print("Target:", details.get("target"))
            print("Amount:", details.get("amount"))
            print("Reason:", details.get("reason"))
            print("Risk score:", details.get("risk_score"))
            print("Message:", details.get("message"))

            response = input(
                "\nType APPROVE to approve, or REJECT to reject: "
            ).strip().upper()

            # Fail closed: every response other than APPROVE rejects.
            approved = response == "APPROVE"

            result = graph.invoke(
                Command(
                    resume={
                        "approved": approved,
                        "fingerprint": details.get("fingerprint"),
                    }
    ),
    config=config,
)

            # The graph normally has one approval interrupt at a time.
            # If it pauses again, the loop handles it.
            break

    print("\n--- V0.7 Final State ---")
    print("Status:", result.get("status"))
    print("Governance:", result.get("governance_decision"))
    print("Approval:", result.get("approval_status"))
    print("Proposal:", result.get("proposal"))
    print("Execution:", result.get("execution_result"))
    print("Response:", result.get("final_response"))

    print("\nAudit Log:")
    for event in result.get("audit_log", []):
        print("-", event)

    return result


if __name__ == "__main__":
    run_agent("Search for recent advances in AI agents")
