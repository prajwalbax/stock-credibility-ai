from __future__ import annotations

import math

from stock_credibility_ai.graph.state import AgentOutput, EvaluationMetrics, ScoreOutput


EXPECTED_AGENTS = {"technical", "sentiment", "fundamental"}
POSITIVE_LABELS = {"bullish", "positive", "strong"}
NEGATIVE_LABELS = {"bearish", "negative", "weak"}


def evaluate_analysis(agent_outputs: dict[str, AgentOutput], score: ScoreOutput) -> EvaluationMetrics:
    confidences = [output.confidence for output in agent_outputs.values()]
    agent_count = len(agent_outputs)
    average_confidence = sum(confidences) / max(agent_count, 1)
    dispersion = _standard_deviation(confidences)
    agreement_score = _agreement_score(agent_outputs)
    conflict_rate = min(len(score.conflicts) / 3, 1)
    data_quality = _data_quality_score(agent_outputs)

    reliability = (
        average_confidence * 0.35
        + agreement_score * 0.25
        + data_quality * 0.25
        + (1 - conflict_rate) * 0.15
    )

    notes: list[str] = []
    if conflict_rate > 0:
        notes.append("Conflicting agent views reduced reliability.")
    if data_quality < 0.75:
        notes.append("Some agents had limited source data or sparse signals.")
    if dispersion > 0.22:
        notes.append("Agent confidence dispersion is elevated.")

    return EvaluationMetrics(
        agent_count=agent_count,
        average_agent_confidence=round(average_confidence, 3),
        confidence_dispersion=round(dispersion, 3),
        agreement_score=round(agreement_score, 3),
        conflict_rate=round(conflict_rate, 3),
        data_quality_score=round(data_quality, 3),
        reliability_score=round(max(0, min(reliability, 1)), 3),
        coverage={agent: agent in agent_outputs for agent in sorted(EXPECTED_AGENTS)},
        notes=notes,
    )


def _standard_deviation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _agreement_score(agent_outputs: dict[str, AgentOutput]) -> float:
    polarities = [_polarity(output.label) for output in agent_outputs.values()]
    non_neutral = [value for value in polarities if value != 0]
    if len(non_neutral) < 2:
        return 0.7
    positive = sum(1 for value in non_neutral if value > 0)
    negative = sum(1 for value in non_neutral if value < 0)
    majority = max(positive, negative)
    return majority / len(non_neutral)


def _polarity(label: str) -> int:
    normalized = label.lower()
    if normalized in POSITIVE_LABELS:
        return 1
    if normalized in NEGATIVE_LABELS:
        return -1
    return 0


def _data_quality_score(agent_outputs: dict[str, AgentOutput]) -> float:
    if not agent_outputs:
        return 0.0
    quality_scores: list[float] = []
    for output in agent_outputs.values():
        evidence_count = len(output.signals) + len(output.risk_flags)
        has_data = bool(output.data)
        score = 0.45 + min(evidence_count, 6) * 0.07 + (0.13 if has_data else 0)
        quality_scores.append(min(score, 1.0))
    return sum(quality_scores) / len(quality_scores)
