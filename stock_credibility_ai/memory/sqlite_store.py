from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from stock_credibility_ai.graph.state import FinalReport
from stock_credibility_ai.utils.config import get_settings


class SQLiteReportStore:
    """Small local audit store for completed committee reports."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or get_settings().sqlite_path)

    async def save_report(self, report: FinalReport) -> None:
        await asyncio.to_thread(self._save_report_sync, report)

    def _save_report_sync(self, report: FinalReport) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    final_score INTEGER NOT NULL,
                    market_bias TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO analysis_reports (
                    ticker, final_score, market_bias, confidence, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report.ticker,
                    report.score.final_score,
                    report.score.market_bias,
                    report.score.confidence,
                    json.dumps(report.model_dump(), default=str),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
