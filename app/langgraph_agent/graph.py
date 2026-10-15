from langgraph.graph import START, END, StateGraph
from app.langgraph_agent.states import AgentState 
from app.langgraph_agent.nodes import agent_node, governor_node, route_after_agent, result_node , followup_node, route_after_followup

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("governor", governor_node)
    workflow.add_node("result", result_node)
    workflow.add_node("followup", followup_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "governance": "governor",
            "stop": END,
        })
    workflow.add_edge("governor", "followup")
    workflow.add_conditional_edges(
        "followup",
        route_after_followup,
        {
            "governance": "governor",
            "result": "result"
        }
    )
    workflow.add_edge("result", END)

    app = workflow.compile()

    return app

