from __future__ import annotations

from stock_credibility_ai.data.preprocessing import clamp
from stock_credibility_ai.graph.state import AgentOutput


def arbitrate(agent_outputs: dict[str, AgentOutput], iteration: int) -> dict[str, object]:
    technical = agent_outputs.get("technical")
    sentiment = agent_outputs.get("sentiment")
    fundamental = agent_outputs.get("fundamental")

    weights = {"technical": 0.36, "sentiment": 0.24, "fundamental": 0.40}
    conflicts: list[str] = []
    reasoning: list[str] = []

    if technical and "high short-term volatility" in technical.risk_flags:
        weights["technical"] -= 0.08
        weights["fundamental"] += 0.05
        weights["sentiment"] += 0.03
        conflicts.append("high short-term volatility reduced technical weighting")

    if technical and sentiment:
        if technical.label in {"bullish", "strong"} and sentiment.label == "negative":
            conflicts.append("technical strength conflicts with negative sentiment")
            weights["sentiment"] += 0.06
        if technical.label == "bearish" and sentiment.label == "positive":
            conflicts.append("positive news sentiment conflicts with weak technicals")
            weights["technical"] += 0.05

    if fundamental and technical:
        if fundamental.label == "weak" and technical.label == "bullish":
            conflicts.append("short-term momentum is ahead of weak fundamentals")
            weights["fundamental"] += 0.07
        if fundamental.label == "strong" and technical.label == "bearish":
            conflicts.append("healthy fundamentals conflict with bearish price action")
            weights["technical"] += 0.04

    normalized_total = sum(weights.values())
    weights = {key: value / normalized_total for key, value in weights.items()}

    weighted_score = 0.0
    confidence_votes: list[float] = []
    for name, output in agent_outputs.items():
        if name in weights:
            weighted_score += output.confidence * weights[name]
            confidence_votes.append(output.confidence)
            reasoning.append(f"{name} view: {output.label} at {output.confidence:.2f} confidence")

    final_score = round(clamp(weighted_score) * 100)
    market_bias = "bullish" if final_score >= 65 else "bearish" if final_score <= 45 else "neutral"
    confidence = round((sum(confidence_votes) / max(len(confidence_votes), 1)) * (1 - min(len(conflicts), 3) * 0.08), 2)

    reanalysis_requests: list[str] = []
    if conflicts and iteration == 0:
        # A serious conflict goes back to the whole committee. This keeps the
        # next round collaborative instead of turning the workflow into a
        # single-agent repair step.
        reanalysis_requests = ["technical", "sentiment", "fundamental"]

    return {
        "final_score": final_score,
        "market_bias": market_bias,
        "confidence": confidence,
        "reasoning": reasoning,
        "conflicts": conflicts,
        "weights": weights,
        "reanalysis_requests": reanalysis_requests,
    }
