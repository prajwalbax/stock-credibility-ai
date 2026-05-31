import logging
from typing import Any

from stock_credibility_ai.utils.config import get_settings

logger = logging.getLogger(__name__)


def build_chat_model() -> Any | None:
    """Create a free/open chat model client when configured.

    The project is intentionally runnable without an LLM. If the requested
    provider package or credentials are missing, callers receive None and can
    use deterministic fallback reporting.
    """

    settings = get_settings()
    provider = settings.llm_provider.lower()

    try:
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(model=settings.ollama_model, temperature=0.2)
        if provider == "groq":
            from langchain_groq import ChatGroq

            if not settings.groq_api_key:
                logger.warning("GROQ_API_KEY is not set; using fallback report generation.")
                return None
            return ChatGroq(model=settings.groq_model, temperature=0.2, api_key=settings.groq_api_key)
        if provider == "huggingface":
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

            if not settings.hf_api_token:
                logger.warning("HF_API_TOKEN is not set; using fallback report generation.")
                return None
            endpoint = HuggingFaceEndpoint(
                repo_id=settings.ollama_model,
                huggingfacehub_api_token=settings.hf_api_token,
                temperature=0.2,
            )
            return ChatHuggingFace(llm=endpoint)
    except Exception as exc:
        logger.warning("LLM provider initialization failed: %s", exc)

    return None
