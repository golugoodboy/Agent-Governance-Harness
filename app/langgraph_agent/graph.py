from langgraph.graph import START, END, StateGraph
from app.langgraph.states import AgentState
from app.langgraph.nodes import agent_node, governor_node

def build_graph():
    workflow = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("governor", governor_node)

    graph.add_edge(START, "agent")
    graph.add_edge("agent", "governor")
    graph.add_edge("governor", END)

    app = workflow.compile()

    return app