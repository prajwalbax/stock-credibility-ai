from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from stock_credibility_ai.graph.state import CredibilityState, ScoreOutput
from stock_credibility_ai.models.arbitration_model import arbitrate

logger = logging.getLogger(__name__)


async def score_agent(state: CredibilityState) -> dict:
    logger.info("Score agent arbitrating %s", state["ticker"])
    result = arbitrate(state.get("agent_outputs", {}), state.get("iteration", 0))
    reanalysis_requests = list(result.pop("reanalysis_requests", []))
    score = ScoreOutput(**result)
    next_iteration = state.get("iteration", 0) + (1 if reanalysis_requests else 0)
    return {
        "score": score,
        "requested_reanalysis": reanalysis_requests,
        "iteration": next_iteration,
        "analyst_memory": [f"Score agent: {score.market_bias} score {score.final_score}"],
        "messages": [AIMessage(content=score.model_dump_json())],
    }
