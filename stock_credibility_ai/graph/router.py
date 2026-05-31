from __future__ import annotations

from langgraph.graph import END

from stock_credibility_ai.graph.state import CredibilityState


ANALYST_NODES = ["technical_agent", "sentiment_agent", "fundamental_agent"]


def route_initial_agents(_: CredibilityState) -> list[str]:
    return ANALYST_NODES


def route_after_score(state: CredibilityState) -> list[str] | str:
    requests = state.get("requested_reanalysis", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)

    if requests and iteration < max_iterations:
        node_map = {
            "technical": "technical_agent",
            "sentiment": "sentiment_agent",
            "fundamental": "fundamental_agent",
        }
        return [node_map[item] for item in requests if item in node_map]
    return "report_agent"


def route_after_report(_: CredibilityState) -> str:
    return END
