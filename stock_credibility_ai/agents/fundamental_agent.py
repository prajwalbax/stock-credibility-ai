from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from stock_credibility_ai.data.market_data import fetch_fundamentals
from stock_credibility_ai.data.preprocessing import clamp, safe_float
from stock_credibility_ai.graph.state import AgentOutput, CredibilityState

logger = logging.getLogger(__name__)


async def fundamental_agent(state: CredibilityState) -> dict:
    ticker = state["ticker"]
    logger.info("Fundamental agent analyzing %s", ticker)
    info = await fetch_fundamentals(ticker)
    output = _evaluate(info)
    return {
        "agent_outputs": {"fundamental": output},
        "analyst_memory": [f"Fundamental agent: {output.label} ({output.confidence:.2f})"],
        "messages": [AIMessage(content=output.model_dump_json())],
    }


def _evaluate(info: dict) -> AgentOutput:
    positives: list[str] = []
    concerns: list[str] = []
    score = 0.5

    pe = safe_float(info.get("trailingPE"), default=0)
    debt_to_equity = safe_float(info.get("debtToEquity"), default=0)
    roe = safe_float(info.get("returnOnEquity"), default=0)
    revenue_growth = safe_float(info.get("revenueGrowth"), default=0)
    market_cap = safe_float(info.get("marketCap"), default=0)
    margins = safe_float(info.get("profitMargins"), default=0)

    if 0 < pe < 35:
        score += 0.09
        positives.append(f"reasonable PE ratio ({pe:.1f})")
    elif pe >= 50:
        score -= 0.08
        concerns.append(f"elevated PE ratio ({pe:.1f})")

    if debt_to_equity and debt_to_equity < 120:
        score += 0.08
        positives.append(f"manageable debt/equity ({debt_to_equity:.1f})")
    elif debt_to_equity >= 200:
        score -= 0.10
        concerns.append(f"high debt/equity ({debt_to_equity:.1f})")

    if roe > 0.12:
        score += 0.10
        positives.append(f"healthy ROE ({roe:.1%})")
    elif roe < 0:
        score -= 0.10
        concerns.append(f"negative ROE ({roe:.1%})")

    if revenue_growth > 0.05:
        score += 0.10
        positives.append(f"revenue growth ({revenue_growth:.1%})")
    elif revenue_growth < -0.03:
        score -= 0.09
        concerns.append(f"revenue contraction ({revenue_growth:.1%})")

    if margins > 0.08:
        score += 0.08
        positives.append(f"positive profit margins ({margins:.1%})")
    elif margins < 0:
        score -= 0.10
        concerns.append(f"negative profit margins ({margins:.1%})")

    if market_cap > 10_000_000_000:
        score += 0.05
        positives.append("large-cap scale")

    confidence = clamp(score)
    label = "strong" if confidence >= 0.66 else "weak" if confidence <= 0.43 else "mixed"

    return AgentOutput(
        agent="fundamental",
        label=label,
        confidence=round(confidence, 2),
        reasoning=["Evaluated PE, debt/equity, ROE, revenue growth, market cap, and margins from yfinance."],
        signals=positives,
        risk_flags=concerns,
        data={
            "pe_ratio": pe,
            "debt_to_equity": debt_to_equity,
            "roe": roe,
            "revenue_growth": revenue_growth,
            "market_cap": market_cap,
            "profit_margins": margins,
        },
    )
