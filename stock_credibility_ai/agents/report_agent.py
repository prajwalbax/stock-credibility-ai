from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage

from stock_credibility_ai.graph.state import CredibilityState, FinalReport
from stock_credibility_ai.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


async def report_agent(state: CredibilityState) -> dict:
    logger.info("Report agent writing final report for %s", state["ticker"])
    score = state["score"]
    agents = state.get("agent_outputs", {})
    narrative = await _generate_narrative(state)
    report = FinalReport(
        ticker=state["ticker"],
        score=score,
        agents=agents,
        narrative=narrative,
        limitations=[
            "This is an educational credibility analysis, not financial advice.",
            "Free data sources can be delayed, incomplete, or temporarily unavailable.",
        ],
    )
    return {
        "final_report": report,
        "requested_reanalysis": [],
        "messages": [AIMessage(content=report.model_dump_json())],
    }


async def _generate_narrative(state: CredibilityState) -> str:
    score = state["score"]
    agent_payload = {
        key: value.model_dump() for key, value in state.get("agent_outputs", {}).items()
    }
    fallback = _fallback_narrative(state)
    llm = build_chat_model()
    if llm is None:
        return fallback

    prompt = (
        "You are the report chair of an investment committee. Write a concise, "
        "analyst-style stock credibility report. Explain why the score was generated, "
        "name conflicts, and avoid financial advice.\n\n"
        f"Ticker: {state['ticker']}\n"
        f"Score: {score.model_dump_json()}\n"
        f"Agent views: {json.dumps(agent_payload, indent=2)}"
    )
    try:
        response = await llm.ainvoke(prompt)
        return str(response.content)
    except Exception as exc:
        logger.warning("LLM report generation failed; using fallback: %s", exc)
        return fallback


def _fallback_narrative(state: CredibilityState) -> str:
    score = state["score"]
    agents = state.get("agent_outputs", {})
    parts = [
        f"{state['ticker']} receives a credibility score of {score.final_score}/100 with a {score.market_bias} market bias.",
    ]
    for name, output in agents.items():
        signals = ", ".join(output.signals[:3]) or "limited constructive signals"
        risks = ", ".join(output.risk_flags[:2]) or "no major flags from this analyst"
        parts.append(f"The {name} analyst is {output.label} at {output.confidence:.2f} confidence, citing {signals}; risks include {risks}.")
    if score.conflicts:
        parts.append("The committee adjusted for conflicts: " + "; ".join(score.conflicts) + ".")
    parts.append("The score reflects arbitration across technical, sentiment, and fundamental evidence rather than a simple average.")
    return " ".join(parts)
