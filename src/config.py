"""统一配置中心。"""
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "ColdChain-QA"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "coldchain"
    POSTGRES_USER: str = "coldchain"
    POSTGRES_PASSWORD: str = "coldchain123"
    DATABASE_URL: str = "postgresql+psycopg://coldchain:coldchain123@localhost:5432/coldchain"

    # Embedding
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 512

    # LLM
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:12434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_LORA_MODEL: str = "coldchain-qwen2.5:3b"
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 1024

    # RAG
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RETRIEVAL_TOP_K: int = 6
    BM25_ENABLED: bool = True
    HYDE_ENABLED: bool = False

    # 路径
    DATA_DIR: Path = Path("./data")
    CACHE_DIR: Path = Path("./cache")
    MODELS_DIR: Path = Path("./models")

    # LoRA 训练
    LORA_BASE_MODEL: str = "Qwen/Qwen2.5-3B-Instruct"
    LORA_OUTPUT_DIR: Path = Path("./models/lora_adapter")
    LORA_R: int = 8
    LORA_ALPHA: int = 16
    LORA_EPOCHS: int = 3
    LORA_BATCH_SIZE: int = 1
    LORA_GRAD_ACCUM: int = 8
    LORA_MAX_SEQ_LEN: int = 1536
    LORA_4BIT: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
