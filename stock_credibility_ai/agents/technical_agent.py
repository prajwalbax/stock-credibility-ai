from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from stock_credibility_ai.data.market_data import fetch_ohlcv
from stock_credibility_ai.graph.state import AgentOutput, CredibilityState
from stock_credibility_ai.models.technical_model import classify_technical

logger = logging.getLogger(__name__)


async def technical_agent(state: CredibilityState) -> dict:
    ticker = state["ticker"]
    logger.info("Technical agent analyzing %s", ticker)
    frame = await fetch_ohlcv(ticker, state.get("period", "1y"), state.get("interval", "1d"))
    result = classify_technical(frame)

    output = AgentOutput(
        agent="technical",
        label=str(result["trend"]),
        confidence=float(result["confidence"]),
        reasoning=[
            "Evaluated RSI, MACD, moving-average alignment, Bollinger position, volatility, volume, and support/resistance."
        ],
        signals=list(result.get("signals", [])),
        risk_flags=list(result.get("risk_flags", [])),
        data={key: value for key, value in result.items() if key not in {"trend", "confidence", "signals", "risk_flags"}},
    )
    return {
        "agent_outputs": {"technical": output},
        "analyst_memory": [f"Technical agent: {output.label} ({output.confidence:.2f})"],
        "messages": [AIMessage(content=output.model_dump_json())],
    }
