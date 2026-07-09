"""Builds the compiled LangGraph state graph for the copilot.

Graph shape:

    START -> orchestrator -> dispatcher -(conditional)-> tax_advisor -> dispatcher
                                          -(conditional)-> not_implemented -> dispatcher
                                          -(conditional)-> responder -> END

The dispatcher/route_from_dispatcher pair implements a supervisor-with-queue
pattern: orchestrator decides *what* needs to happen (a list of subtasks),
dispatcher decides *one step at a time* which specialist handles the next
item, looping until the queue is empty and everything routes to responder.
Verification (Task 7) will sit between dispatcher and responder once the
Financial Planner exists to give it something numeric to check.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.dispatcher import dispatcher_node, route_from_dispatcher
from app.graph.nodes.expense_tracker import expense_tracker_node
from app.graph.nodes.not_implemented import not_implemented_node
from app.graph.nodes.orchestrator import orchestrator_node
from app.graph.nodes.responder import responder_node
from app.graph.nodes.tax_advisor import tax_advisor_node
from app.graph.state import CopilotState


def _build_graph():
    graph = StateGraph(CopilotState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("dispatcher", dispatcher_node)
    graph.add_node("tax_advisor", tax_advisor_node)
    graph.add_node("expense_tracker", expense_tracker_node)
    graph.add_node("not_implemented", not_implemented_node)
    graph.add_node("responder", responder_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "dispatcher")
    graph.add_conditional_edges(
        "dispatcher",
        route_from_dispatcher,
        {
            "tax_advisor": "tax_advisor",
            "expense_tracker": "expense_tracker",
            "not_implemented": "not_implemented",
            "responder": "responder",
        },
    )
    graph.add_edge("tax_advisor", "dispatcher")
    graph.add_edge("expense_tracker", "dispatcher")
    graph.add_edge("not_implemented", "dispatcher")
    graph.add_edge("responder", END)

    return graph.compile()


@lru_cache
def get_compiled_graph():
    return _build_graph()
