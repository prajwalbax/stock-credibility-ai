from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from stock_credibility_ai.data.news_data import fetch_google_news
from stock_credibility_ai.graph.state import AgentOutput, CredibilityState
from stock_credibility_ai.models.sentiment_model import analyze_headlines

logger = logging.getLogger(__name__)


async def sentiment_agent(state: CredibilityState) -> dict:
    ticker = state["ticker"]
    logger.info("Sentiment agent analyzing %s", ticker)
    news_items = await fetch_google_news(ticker)
    headlines = [item.title for item in news_items]
    result = analyze_headlines(headlines)

    output = AgentOutput(
        agent="sentiment",
        label=str(result["sentiment"]),
        confidence=float(result["confidence"]),
        reasoning=["Reviewed Google News RSS headlines and extracted narrative polarity."],
        signals=list(result.get("key_topics", [])),
        risk_flags=[] if result["sentiment"] != "negative" else ["negative media narrative"],
        data={
            "headline_summary": result.get("headline_summary", ""),
            "headlines": headlines[:10],
            "sources": [item.source for item in news_items[:10] if item.source],
        },
    )
    return {
        "agent_outputs": {"sentiment": output},
        "analyst_memory": [f"Sentiment agent: {output.label} ({output.confidence:.2f})"],
        "messages": [AIMessage(content=output.model_dump_json())],
    }
