from __future__ import annotations

from stock_credibility_ai.graph.state import (
    AgentOutput,
    ExplainabilityReport,
    ExplanationItem,
    ScoreOutput,
)


POSITIVE_LABELS = {"bullish", "positive", "strong"}
NEGATIVE_LABELS = {"bearish", "negative", "weak"}


def explain_decision(agent_outputs: dict[str, AgentOutput], score: ScoreOutput) -> ExplainabilityReport:
    contributions = {
        name: round(score.weights.get(name, 0) * output.confidence * 100, 2)
        for name, output in agent_outputs.items()
    }

    positive: list[ExplanationItem] = []
    negative: list[ExplanationItem] = []
    for name, output in agent_outputs.items():
        weight = score.weights.get(name, 0)
        polarity = _polarity(output.label)
        base_impact = round(weight * output.confidence * 100, 2)

        if polarity >= 0:
            for signal in output.signals[:4]:
                positive.append(
                    ExplanationItem(
                        feature=f"{name}_signal",
                        source=name,
                        direction="positive",
                        impact=round(base_impact / max(len(output.signals[:4]), 1), 2),
                        evidence=signal,
                    )
                )
        if polarity <= 0 or output.risk_flags:
            for flag in output.risk_flags[:4]:
                negative.append(
                    ExplanationItem(
                        feature=f"{name}_risk",
                        source=name,
                        direction="negative",
                        impact=round((weight * max(output.confidence, 0.35) * 100) / max(len(output.risk_flags[:4]), 1), 2),
                        evidence=flag,
                    )
                )

    positive.sort(key=lambda item: item.impact, reverse=True)
    negative.sort(key=lambda item: item.impact, reverse=True)

    trace = [
        "Analyst agents produced independent structured outputs.",
        "The score agent adjusted weights based on confidence, volatility, and cross-agent conflicts.",
        f"Final score resolved to {score.final_score}/100 with {score.market_bias} bias.",
    ]
    if score.conflicts:
        trace.append("Conflict adjustments applied: " + "; ".join(score.conflicts))

    return ExplainabilityReport(
        methodology=(
            "Transparent weighted arbitration. Agent confidence, dynamic weights, "
            "positive signals, and risk flags are exposed as local decision factors."
        ),
        agent_contributions=contributions,
        top_positive_factors=positive[:6],
        top_negative_factors=negative[:6],
        decision_trace=trace,
    )


def _polarity(label: str) -> int:
    normalized = label.lower()
    if normalized in POSITIVE_LABELS:
        return 1
    if normalized in NEGATIVE_LABELS:
        return -1
    return 0
