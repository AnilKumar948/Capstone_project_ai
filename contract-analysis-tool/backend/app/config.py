from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LiteLLM configuration (if using LiteLLM proxy)
    litellm_proxy_url: str = Field(default="")
    litellm_api_key: str = Field(default="")
    litellm_embedding_model: str = Field(default="text-embedding-3-large")
    
    # Direct LLM configuration (fallback if LiteLLM not available)
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4o")
    llm_fallback_model: str = Field(default="claude-sonnet-4-6")
    llm_temperature: float = Field(default=0.1)
    llm_max_tokens: int = Field(default=4096)

    database_url: str = Field(default="postgresql+asyncpg://user:pass@db:5432/contracts")
    redis_url: str = Field(default="redis://redis:6379/0")

    s3_bucket: str = Field(default="contract-uploads")
    s3_endpoint_url: str = Field(default="http://minio:9000")
    aws_access_key_id: str = Field(default="minioadmin")
    aws_secret_access_key: str = Field(default="minioadmin")
    local_storage_dir: str = Field(default="./backend/local_storage")
    use_local_storage_fallback: bool = Field(default=True)

    pinecone_api_key: str = Field(default="")
    pinecone_index: str = Field(default="contract-clauses")
    vector_dimension: int = Field(default=1536)

    secret_key: str = Field(default="change-me-in-production")
    jwt_expire_minutes: int = Field(default=60)

    celery_broker_url: str = Field(default="redis://redis:6379/1")
    celery_result_backend: str = Field(default="redis://redis:6379/2")

    tesseract_cmd: str = Field(default="/usr/bin/tesseract")
    
    @property
    def use_litellm(self) -> bool:
        """Check if LiteLLM configuration is available."""
        return bool(self.litellm_proxy_url and self.litellm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
