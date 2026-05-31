from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote_plus

from stock_credibility_ai.data.preprocessing import dedupe_texts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    published: str | None = None
    source: str | None = None


async def fetch_google_news(ticker: str, limit: int = 20) -> list[NewsItem]:
    """Fetch latest free headlines from Google News RSS."""

    query = quote_plus(f"{ticker} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def _fetch() -> list[NewsItem]:
        import feedparser

        feed = feedparser.parse(url)
        titles = dedupe_texts(entry.get("title", "") for entry in feed.entries)
        items: list[NewsItem] = []
        for title in titles[:limit]:
            entry = next((item for item in feed.entries if item.get("title") == title), {})
            items.append(
                NewsItem(
                    title=title,
                    link=entry.get("link", ""),
                    published=entry.get("published") or datetime.utcnow().isoformat(),
                    source=entry.get("source", {}).get("title") if isinstance(entry.get("source"), dict) else None,
                )
            )
        return items

    try:
        return await asyncio.to_thread(_fetch)
    except Exception as exc:
        logger.exception("Failed to fetch Google News RSS for %s: %s", ticker, exc)
        return []
