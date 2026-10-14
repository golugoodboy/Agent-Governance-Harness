from langgraph.graph import START, END, StateGraph
from app.langgraph_agent.states import AgentState 
from app.langgraph_agent.nodes import agent_node, governor_node, route_after_agent

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("governor", governor_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "governor": "governor",
            "stop": END,
        })
    workflow.add_edge("governor", END)

    app = workflow.compile()

    return app
