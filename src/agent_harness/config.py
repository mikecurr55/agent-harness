"""Centralised configuration loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # Identity provider (external IdP for temporal credentials)
    identity_provider_url: str = ""
    identity_provider_client_id: str = ""
    identity_provider_client_secret: str = ""

    # Audit
    audit_db_url: str = "sqlite+aiosqlite:///audit.db"

    # Policy
    policy_dir: Path = Path("policies/")


settings = Settings()
