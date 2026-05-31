from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentOutput(BaseModel):
    agent: str
    label: str
    confidence: float = Field(ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class ScoreOutput(BaseModel):
    final_score: int = Field(ge=0, le=100)
    market_bias: Literal["bullish", "neutral", "bearish"]
    confidence: float = Field(ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)


class FinalReport(BaseModel):
    ticker: str
    score: ScoreOutput
    agents: dict[str, AgentOutput]
    narrative: str
    limitations: list[str] = Field(default_factory=list)


def merge_agent_outputs(left: dict[str, AgentOutput], right: dict[str, AgentOutput]) -> dict[str, AgentOutput]:
    return {**left, **right}


def overwrite(left: Any, right: Any) -> Any:
    return right if right is not None else left


class CredibilityState(TypedDict, total=False):
    ticker: str
    period: str
    interval: str
    max_iterations: int
    iteration: Annotated[int, overwrite]
    requested_reanalysis: Annotated[list[str], overwrite]
    agent_outputs: Annotated[dict[str, AgentOutput], merge_agent_outputs]
    score: Annotated[ScoreOutput | None, overwrite]
    final_report: Annotated[FinalReport | None, overwrite]
    analyst_memory: Annotated[list[str], operator.add]
    messages: Annotated[list[BaseMessage], add_messages]
    errors: Annotated[list[str], operator.add]
