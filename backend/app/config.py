"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "KnowledgePilot AI"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    api_version: str = "v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = "sqlite+aiosqlite:///./knowledgepilot.db"

    # Redis
    redis_url: str | None = None

    # JWT
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Vector Database
    vector_db_type: Literal["chromadb", "pinecone", "faiss"] = "chromadb"
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "knowledgepilot"

    # Pinecone
    pinecone_api_key: str | None = None
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "knowledgepilot"

    # Document Processing
    max_file_size_mb: int = 50
    allowed_extensions: str = "pdf,docx,md,txt,html"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Embedding
    embedding_provider: Literal["openai", "sentence-transformers", "bge"] = "openai"
    embedding_batch_size: int = 100
    embedding_dimension: int = 1536

    # RAG
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7
    rag_rerank_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Get allowed extensions as a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
