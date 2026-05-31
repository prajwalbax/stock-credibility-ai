from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from stock_credibility_ai.graph.state import FinalReport
from stock_credibility_ai.graph.workflow import analyze_stock

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Stock Credibility AI",
    version="0.1.0",
    description="Multi-agent stock credibility analysis with LangChain and LangGraph.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AnalysisRequest(BaseModel):
    ticker: str = Field(min_length=1, examples=["AAPL"])
    period: str = "1y"
    interval: str = "1d"
    max_iterations: int = Field(default=2, ge=0, le=4)


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinalReport)
async def analyze(request: AnalysisRequest) -> FinalReport:
    try:
        return await analyze_stock(
            ticker=request.ticker,
            period=request.period,
            interval=request.interval,
            max_iterations=request.max_iterations,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
