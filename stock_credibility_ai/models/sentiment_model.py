from __future__ import annotations

import logging
from functools import lru_cache

from stock_credibility_ai.data.preprocessing import clamp
from stock_credibility_ai.utils.config import get_settings

logger = logging.getLogger(__name__)

POSITIVE_TERMS = {
    "beat",
    "growth",
    "upgrade",
    "profit",
    "strong",
    "surge",
    "record",
    "buy",
    "expansion",
    "optimism",
    "rally",
    "outperform",
}
NEGATIVE_TERMS = {
    "miss",
    "downgrade",
    "loss",
    "weak",
    "fall",
    "lawsuit",
    "probe",
    "debt",
    "cuts",
    "slump",
    "sell",
    "underperform",
}


@lru_cache
def _pipeline():
    settings = get_settings()
    if not settings.enable_transformers:
        return None
    try:
        from transformers import pipeline

        return pipeline("sentiment-analysis", model=settings.sentiment_model_name)
    except Exception as exc:
        logger.warning("Transformer sentiment unavailable; using lexicon fallback: %s", exc)
        return None


def analyze_headlines(headlines: list[str]) -> dict[str, object]:
    if not headlines:
        return {
            "sentiment": "neutral",
            "confidence": 0.35,
            "headline_summary": "No recent Google News headlines were available.",
            "key_topics": [],
        }

    classifier = _pipeline()
    if classifier:
        results = classifier(headlines[:16], truncation=True)
        signed_scores: list[float] = []
        for result in results:
            label = str(result["label"]).lower()
            score = float(result["score"])
            if "pos" in label:
                signed_scores.append(score)
            elif "neg" in label:
                signed_scores.append(-score)
            else:
                signed_scores.append(0)
        mean_score = sum(signed_scores) / max(len(signed_scores), 1)
    else:
        mean_score = _lexicon_score(headlines)

    confidence = clamp(0.5 + abs(mean_score) / 2)
    sentiment = "positive" if mean_score > 0.12 else "negative" if mean_score < -0.12 else "neutral"
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "headline_summary": _summarize(headlines),
        "key_topics": _key_topics(headlines),
    }


def _lexicon_score(headlines: list[str]) -> float:
    score = 0
    total = 0
    for headline in headlines:
        words = {word.strip(".,:;!?()[]'\"").lower() for word in headline.split()}
        score += len(words & POSITIVE_TERMS)
        score -= len(words & NEGATIVE_TERMS)
        total += max(len(words), 1)
    return clamp(score / max(total, 1) * 8, -1, 1)


def _summarize(headlines: list[str]) -> str:
    sample = headlines[:3]
    return " | ".join(sample)


def _key_topics(headlines: list[str]) -> list[str]:
    stop = {"the", "and", "for", "with", "from", "stock", "stocks", "shares", "market", "says"}
    counts: dict[str, int] = {}
    for headline in headlines:
        for token in headline.lower().replace("-", " ").split():
            cleaned = token.strip(".,:;!?()[]'\"")
            if len(cleaned) > 4 and cleaned not in stop:
                counts[cleaned] = counts.get(cleaned, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:6]]
