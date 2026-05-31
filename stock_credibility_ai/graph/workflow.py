from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from stock_credibility_ai.agents.fundamental_agent import fundamental_agent
from stock_credibility_ai.agents.report_agent import report_agent
from stock_credibility_ai.agents.score_agent import score_agent
from stock_credibility_ai.agents.sentiment_agent import sentiment_agent
from stock_credibility_ai.agents.technical_agent import technical_agent
from stock_credibility_ai.graph.router import route_after_report, route_after_score, route_initial_agents
from stock_credibility_ai.graph.state import CredibilityState, FinalReport
from stock_credibility_ai.memory.chroma_memory import ChromaMemory
from stock_credibility_ai.memory.sqlite_store import SQLiteReportStore
from stock_credibility_ai.utils.logging import configure_logging

logger = logging.getLogger(__name__)


async def orchestrator(state: CredibilityState) -> dict[str, Any]:
    ticker = state["ticker"].upper()
    memory = ChromaMemory()
    recalled = memory.query(ticker, f"recent analyst notes for {ticker}")
    return {
        "ticker": ticker,
        "iteration": state.get("iteration", 0),
        "requested_reanalysis": [],
        "analyst_memory": [f"Committee opened review for {ticker}.", *recalled],
        "messages": [HumanMessage(content=f"Analyze stock credibility for {ticker}.")],
    }


async def committee_sync(state: CredibilityState) -> dict[str, Any]:
    completed = ", ".join(sorted(state.get("agent_outputs", {}).keys()))
    logger.info("Committee sync received analysts: %s", completed)
    return {"analyst_memory": [f"Committee sync received: {completed}."]}


def build_graph():
    workflow = StateGraph(CredibilityState)
    workflow.add_node("orchestrator", orchestrator)
    workflow.add_node("technical_agent", technical_agent)
    workflow.add_node("sentiment_agent", sentiment_agent)
    workflow.add_node("fundamental_agent", fundamental_agent)
    workflow.add_node("committee_sync", committee_sync)
    workflow.add_node("score_agent", score_agent)
    workflow.add_node("report_agent", report_agent)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges("orchestrator", route_initial_agents)
    workflow.add_edge(["technical_agent", "sentiment_agent", "fundamental_agent"], "committee_sync")
    workflow.add_edge("committee_sync", "score_agent")
    workflow.add_conditional_edges("score_agent", route_after_score)
    workflow.add_conditional_edges("report_agent", route_after_report, {END: END})
    return workflow.compile()


async def analyze_stock(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    max_iterations: int = 2,
) -> FinalReport:
    configure_logging()
    app = build_graph()
    initial_state: CredibilityState = {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "max_iterations": max_iterations,
        "iteration": 0,
        "requested_reanalysis": [],
        "agent_outputs": {},
        "analyst_memory": [],
        "messages": [],
        "errors": [],
    }
    result = await app.ainvoke(initial_state)
    final_report = result.get("final_report")
    if final_report is None:
        raise RuntimeError("Analysis completed without a final report.")

    memory = ChromaMemory()
    memory.add_note(ticker.upper(), final_report.narrative)
    await SQLiteReportStore().save_report(final_report)
    return final_report
