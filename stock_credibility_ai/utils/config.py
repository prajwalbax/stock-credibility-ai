from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")

    hf_api_token: str | None = Field(default=None, alias="HF_API_TOKEN")
    alpha_vantage_api_key: str | None = Field(default=None, alias="ALPHA_VANTAGE_API_KEY")
    finnhub_api_key: str | None = Field(default=None, alias="FINNHUB_API_KEY")

    chroma_path: str = Field(default="./.chroma", alias="CHROMA_PATH")
    sqlite_path: str = Field(default="./stock_credibility.sqlite3", alias="SQLITE_PATH")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    sentiment_model_name: str = Field(
        default="ProsusAI/finbert",
        alias="SENTIMENT_MODEL_NAME",
    )

    enable_transformers: bool = Field(
        default=False,
        alias="ENABLE_TRANSFORMERS",
    )

    enable_llm_report: bool = Field(
        default=True,
        alias="ENABLE_LLM_REPORT",
    )

    report_llm_timeout_seconds: float = Field(
        default=20.0,
        alias="REPORT_LLM_TIMEOUT_SECONDS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
