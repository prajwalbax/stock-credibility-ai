from __future__ import annotations

import pandas as pd

from stock_credibility_ai.data.preprocessing import clamp


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    close = data["Close"]

    data["sma_20"] = close.rolling(20).mean()
    data["sma_50"] = close.rolling(50).mean()
    data["ema_20"] = close.ewm(span=20, adjust=False).mean()
    data["ema_50"] = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    data["rsi"] = 100 - (100 / (1 + rs))

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    data["macd"] = ema_12 - ema_26
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()

    rolling_std = close.rolling(20).std()
    data["bb_upper"] = data["sma_20"] + (2 * rolling_std)
    data["bb_lower"] = data["sma_20"] - (2 * rolling_std)
    data["volatility"] = close.pct_change().rolling(20).std()
    data["volume_sma_20"] = data["Volume"].rolling(20).mean()
    return data.dropna()


def support_resistance(frame: pd.DataFrame, window: int = 20) -> tuple[float | None, float | None]:
    if frame.empty or len(frame) < window:
        return None, None
    recent = frame.tail(window)
    return float(recent["Low"].min()), float(recent["High"].max())


def classify_technical(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty or len(frame) < 60:
        return {
            "trend": "unknown",
            "confidence": 0.25,
            "signals": [],
            "risk_flags": ["insufficient OHLCV history"],
        }

    data = add_indicators(frame)
    if data.empty:
        return {
            "trend": "unknown",
            "confidence": 0.25,
            "signals": [],
            "risk_flags": ["indicator calculation failed"],
        }

    latest = data.iloc[-1]
    previous = data.iloc[-2]
    signals: list[str] = []
    risks: list[str] = []
    score = 0.5

    if latest["ema_20"] > latest["ema_50"]:
        score += 0.12
        signals.append("EMA20 above EMA50")
    else:
        score -= 0.12
        risks.append("EMA20 below EMA50")

    if latest["sma_20"] > latest["sma_50"]:
        score += 0.08
        signals.append("SMA20 above SMA50")
    else:
        score -= 0.08
        risks.append("SMA20 below SMA50")

    if previous["macd"] <= previous["macd_signal"] and latest["macd"] > latest["macd_signal"]:
        score += 0.12
        signals.append("MACD bullish crossover")
    elif latest["macd"] > latest["macd_signal"]:
        score += 0.07
        signals.append("MACD above signal line")
    else:
        score -= 0.07
        risks.append("MACD below signal line")

    if 45 <= latest["rsi"] <= 70:
        score += 0.08
        signals.append(f"RSI constructive at {latest['rsi']:.1f}")
    elif latest["rsi"] > 75:
        score -= 0.06
        risks.append(f"RSI overbought at {latest['rsi']:.1f}")
    elif latest["rsi"] < 35:
        score -= 0.08
        risks.append(f"RSI weak at {latest['rsi']:.1f}")

    if latest["Volume"] > latest["volume_sma_20"]:
        score += 0.05
        signals.append("volume above 20-day average")

    support, resistance = support_resistance(data)
    if resistance and latest["Close"] >= resistance * 0.97:
        risks.append("near resistance zone")
        score -= 0.04
    if support and latest["Close"] <= support * 1.03:
        risks.append("near support zone")

    volatility = float(latest["volatility"])
    if volatility > 0.04:
        risks.append("high short-term volatility")
        score -= 0.07

    confidence = clamp(score)
    trend = "bullish" if confidence >= 0.62 else "bearish" if confidence <= 0.42 else "neutral"

    return {
        "trend": trend,
        "confidence": round(confidence, 2),
        "signals": signals,
        "risk_flags": risks,
        "support": support,
        "resistance": resistance,
        "volatility": volatility,
    }
