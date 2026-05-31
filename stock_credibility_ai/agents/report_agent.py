from __future__ import annotations

import json
import logging
import asyncio

from langchain_core.messages import AIMessage

from stock_credibility_ai.graph.state import CredibilityState, FinalReport
from stock_credibility_ai.models.evaluation_model import evaluate_analysis
from stock_credibility_ai.models.explainability_model import explain_decision
from stock_credibility_ai.utils.config import get_settings
from stock_credibility_ai.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


async def report_agent(state: CredibilityState) -> dict:
    try:
        logger.info("Report agent writing final report for %s", state["ticker"])

        score = state["score"]
        agents = state.get("agent_outputs", {})

        logger.info("STEP 1: Starting evaluation")
        evaluation = evaluate_analysis(agents, score)

        logger.info("STEP 2: Starting explainability")
        explainability = explain_decision(agents, score)

        logger.info("STEP 3: Generating narrative")
        narrative = await _generate_narrative(state)

        logger.info("STEP 4: Building FinalReport")
        report = FinalReport(
            ticker=state["ticker"],
            score=score,
            agents=agents,
            narrative=narrative,
            evaluation=evaluation,
            explainability=explainability,
            limitations=[
                "This is an educational credibility analysis, not financial advice.",
                "Free data sources can be delayed, incomplete, or temporarily unavailable.",
            ],
        )

        logger.info("STEP 5: Serializing report")
        payload = report.model_dump_json()

        logger.info("STEP 6: Returning response")

        return {
            "final_report": report,
            "requested_reanalysis": [],
            "messages": [AIMessage(content=payload)],
        }

    except Exception as exc:
        logger.exception("REPORT AGENT FAILED: %s", exc)
        raise


async def _generate_narrative(state: CredibilityState) -> str:
    score = state["score"]

    agent_payload = {
        key: value.model_dump()
        for key, value in state.get("agent_outputs", {}).items()
    }

    fallback = _fallback_narrative(state)

    settings = get_settings()

    if not settings.enable_llm_report:
        return fallback

    llm = build_chat_model()

    if llm is None:
        return fallback

    prompt = (
        "Write one concise analyst-style stock credibility summary in 120-160 words. "
        "Explain the score, mention key conflicts, and avoid financial advice.\n\n"
        f"Ticker: {state['ticker']}\n"
        f"Score: {score.model_dump_json()}\n"
        f"Agent views: {json.dumps(_compact_agent_payload(agent_payload), separators=(',', ':'))}"
    )

    try:
        response = await asyncio.wait_for(
            llm.ainvoke(prompt),
            timeout=settings.report_llm_timeout_seconds,
        )

        return str(response.content)

    except TimeoutError:
        logger.warning(
            "LLM report generation exceeded %.1fs; using fallback.",
            settings.report_llm_timeout_seconds,
        )
        return fallback

    except Exception as exc:
        logger.warning(
            "LLM report generation failed; using fallback: %s",
            exc,
        )
        return fallback


def _compact_agent_payload(agent_payload: dict) -> dict:
    compact = {}

    for name, payload in agent_payload.items():
        compact[name] = {
            "label": payload.get("label"),
            "confidence": payload.get("confidence"),
            "signals": payload.get("signals", [])[:4],
            "risk_flags": payload.get("risk_flags", [])[:4],
        }

    return compact


def _fallback_narrative(state: CredibilityState) -> str:
    score = state["score"]
    agents = state.get("agent_outputs", {})

    parts = [
        f"{state['ticker']} receives a credibility score of "
        f"{score.final_score}/100 with a {score.market_bias} market bias."
    ]

    for name, output in agents.items():
        signals = ", ".join(output.signals[:3]) or "limited constructive signals"
        risks = ", ".join(output.risk_flags[:2]) or "no major flags from this analyst"

        parts.append(
            f"The {name} analyst is {output.label} at "
            f"{output.confidence:.2f} confidence, citing {signals}; "
            f"risks include {risks}."
        )

    if score.conflicts:
        parts.append(
            "The committee adjusted for conflicts: "
            + "; ".join(score.conflicts)
            + "."
        )

    parts.append(
        "The score reflects arbitration across technical, sentiment, "
        "and fundamental evidence rather than a simple average."
    )

    return " ".join(parts)