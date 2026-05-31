from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


async def fetch_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance using yfinance."""

    def _download() -> pd.DataFrame:
        import yfinance as yf

        frame = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        return frame.dropna()

    try:
        return await asyncio.to_thread(_download)
    except Exception as exc:
        logger.exception("Failed to fetch OHLCV for %s: %s", ticker, exc)
        return pd.DataFrame()


async def fetch_fundamentals(ticker: str) -> dict[str, Any]:
    """Fetch free company fundamentals from Yahoo Finance."""

    def _info() -> dict[str, Any]:
        import yfinance as yf

        return dict(yf.Ticker(ticker).info or {})

    try:
        return await asyncio.to_thread(_info)
    except Exception as exc:
        logger.exception("Failed to fetch fundamentals for %s: %s", ticker, exc)
        return {}


async def fetch_company_context(ticker: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    return await asyncio.gather(
        fetch_ohlcv(ticker),
        fetch_fundamentals(ticker),
    )
