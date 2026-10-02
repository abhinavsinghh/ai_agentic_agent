from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    analyze_source,
    plan_queries,
    reflect,
    route_to_analysis,
    search,
    should_continue,
    write_report,
)
from app.agents.state import ResearchState


def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("plan", plan_queries)
    graph.add_node("search", search)
    graph.add_node("analyze_source", analyze_source)
    graph.add_node("reflect", reflect)
    graph.add_node("write_report", write_report)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_conditional_edges("search", route_to_analysis, ["analyze_source", "reflect"])
    graph.add_edge("analyze_source", "reflect")
    graph.add_conditional_edges("reflect", should_continue, ["search", "write_report"])
    graph.add_edge("write_report", END)

    return graph.compile()
