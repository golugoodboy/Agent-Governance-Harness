from app.langgraph_agent.graph import build_graph

def run_agent(user_request):

    app = build_graph()

    print("\n" + "=" * 70)
    print("LANGGRAPH GOVERNANCE TEST")
    print("=" * 70)

    print(f"\nUser Request: {user_request}")

    result = graph.invoke({
        "user_request" : user_request,
        "status" : "Pending"
    })

    print("\nFinal Graph State")
    print(result)

    return result

if __name__ == "__main__":

    run_agent(
        "Please send an email to the customer"
    )


    