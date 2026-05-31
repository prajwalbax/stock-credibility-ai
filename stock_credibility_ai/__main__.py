from __future__ import annotations

import argparse
import asyncio
import json

from stock_credibility_ai.graph.workflow import analyze_stock


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the stock credibility analyst committee.")
    parser.add_argument("ticker", help="Ticker symbol, for example AAPL or RELIANCE.NS")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--max-iterations", type=int, default=2)
    args = parser.parse_args()

    report = await analyze_stock(args.ticker, args.period, args.interval, args.max_iterations)
    print(json.dumps(report.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
