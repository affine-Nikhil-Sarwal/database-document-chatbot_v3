"""Application settings loaded from repo-root .env via absolute path."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_openai_endpoint: str = Field(default="", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", validation_alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        validation_alias="AZURE_OPENAI_API_VERSION",
    )
    azure_openai_api_base: str = Field(default="", validation_alias="AZURE_OPENAI_API_BASE")
    gpt4_llm_model_deployment_name: str = Field(
        default="",
        validation_alias="GPT4_LLM_MODEL_DEPLOYMENT_NAME",
    )
    embedding_model_deployment_name: str = Field(
        default="",
        validation_alias="EMBEDDING_MODEL_DEPLOYMENT_NAME",
    )

    azure_search_service_endpoint: str = Field(
        default="",
        validation_alias="AZURE_SEARCH_SERVICE_ENDPOINT",
    )
    azure_search_api_key: str = Field(default="", validation_alias="AZURE_SEARCH_API_KEY")
    azure_search_index_name: str = Field(
        default="dupont_email_demo",
        validation_alias="AZURE_SEARCH_INDEX_NAME",
    )
    azure_search_semantic_config_name: str = Field(
        default="my-semantic-config",
        validation_alias="AZURE_SEARCH_SEMANTIC_CONFIG_NAME",
    )
    azure_search_vector_field_name: str = Field(
        default="content_vector",
        validation_alias="AZURE_SEARCH_VECTOR_FIELD_NAME",
    )
    azure_search_document_id_field_name: str = Field(
        default="id",
        validation_alias="AZURE_SEARCH_DOCUMENT_ID_FIELD_NAME",
    )

    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    sql_server: str = Field(default="", validation_alias="SQL_SERVER")
    sql_database: str = Field(default="", validation_alias="SQL_DATABASE")
    sql_username: str = Field(default="", validation_alias="SQL_USERNAME")
    sql_password: str = Field(default="", validation_alias="SQL_PASSWORD")
    sql_driver: str = Field(default="ODBC Driver 18 for SQL Server", validation_alias="SQL_DRIVER")
    sql_schema: str = Field(default="dbo", validation_alias="SQL_SCHEMA")

    workflow_dry_run: bool = Field(default=False, validation_alias="WORKFLOW_DRY_RUN")

    @model_validator(mode="after")
    def normalize_aliases(self) -> Settings:
        if not self.azure_openai_api_base.strip() and self.azure_openai_endpoint.strip():
            object.__setattr__(self, "azure_openai_api_base", self.azure_openai_endpoint.strip())
        if not self.azure_openai_endpoint.strip() and self.azure_openai_api_base.strip():
            object.__setattr__(self, "azure_openai_endpoint", self.azure_openai_api_base.strip())
        if not self.gpt4_llm_model_deployment_name.strip() and self.azure_openai_deployment.strip():
            object.__setattr__(
                self,
                "gpt4_llm_model_deployment_name",
                self.azure_openai_deployment.strip(),
            )
        if not self.azure_openai_deployment.strip() and self.gpt4_llm_model_deployment_name.strip():
            object.__setattr__(
                self,
                "azure_openai_deployment",
                self.gpt4_llm_model_deployment_name.strip(),
            )
        return self

    def require_azure_openai(self) -> None:
        missing: list[str] = []
        if not self.azure_openai_api_key.strip():
            missing.append("AZURE_OPENAI_API_KEY")
        endpoint = self.resolved_azure_endpoint()
        if not endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_BASE")
        deployment = self.resolved_chat_deployment()
        if not deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT or GPT4_LLM_MODEL_DEPLOYMENT_NAME")
        if missing:
            raise ConfigurationError(
                "Missing required Azure OpenAI configuration: " + ", ".join(missing)
            )

    def require_azure_search(self) -> None:
        missing: list[str] = []
        if not self.azure_search_service_endpoint.strip():
            missing.append("AZURE_SEARCH_SERVICE_ENDPOINT")
        if not self.azure_search_api_key.strip():
            missing.append("AZURE_SEARCH_API_KEY")
        if missing:
            raise ConfigurationError(
                "Missing required Azure Search configuration: " + ", ".join(missing)
            )

    def require_embedding_deployment(self) -> None:
        if not self.embedding_model_deployment_name.strip():
            raise ConfigurationError("Set EMBEDDING_MODEL_DEPLOYMENT_NAME")

    def require_database(self) -> None:
        if self.database_url.strip():
            return
        missing = [
            name
            for name, value in [
                ("SQL_SERVER", self.sql_server),
                ("SQL_DATABASE", self.sql_database),
                ("SQL_USERNAME", self.sql_username),
                ("SQL_PASSWORD", self.sql_password),
            ]
            if not str(value).strip()
        ]
        if missing:
            raise ConfigurationError(
                "Missing database configuration. Set DATABASE_URL or: "
                + ", ".join(missing)
            )

    def resolved_azure_endpoint(self) -> str:
        return self.azure_openai_api_base.strip() or self.azure_openai_endpoint.strip()

    def resolved_chat_deployment(self) -> str:
        return (
            self.azure_openai_deployment.strip()
            or self.gpt4_llm_model_deployment_name.strip()
        )

    def export_to_environ(self) -> None:
        """Push normalized settings into os.environ for frozen reuse agents."""
        mapping = {
            "AZURE_OPENAI_API_KEY": self.azure_openai_api_key,
            "AZURE_OPENAI_API_BASE": self.resolved_azure_endpoint(),
            "AZURE_OPENAI_ENDPOINT": self.resolved_azure_endpoint(),
            "AZURE_OPENAI_API_VERSION": self.azure_openai_api_version,
            "AZURE_OPENAI_DEPLOYMENT": self.resolved_chat_deployment(),
            "GPT4_LLM_MODEL_DEPLOYMENT_NAME": self.resolved_chat_deployment(),
            "EMBEDDING_MODEL_DEPLOYMENT_NAME": self.embedding_model_deployment_name,
            "AZURE_SEARCH_SERVICE_ENDPOINT": self.azure_search_service_endpoint,
            "AZURE_SEARCH_API_KEY": self.azure_search_api_key,
            "AZURE_SEARCH_INDEX_NAME": self.azure_search_index_name,
            "AZURE_SEARCH_SEMANTIC_CONFIG": self.azure_search_semantic_config_name,
            "AZURE_SEARCH_SEMANTIC_CONFIG_NAME": self.azure_search_semantic_config_name,
            "AZURE_SEARCH_VECTOR_FIELD_NAME": self.azure_search_vector_field_name,
            "AZURE_SEARCH_DOCUMENT_ID_FIELD_NAME": self.azure_search_document_id_field_name,
            "DATABASE_URL": self.database_url,
            "SQL_SERVER": self.sql_server,
            "SQL_DATABASE": self.sql_database,
            "SQL_USERNAME": self.sql_username,
            "SQL_PASSWORD": self.sql_password,
            "SQL_DRIVER": self.sql_driver,
            "SQL_SCHEMA": self.sql_schema,
        }
        for key, value in mapping.items():
            if value:
                os.environ[key] = str(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["ConfigurationError", "Settings", "get_settings", "_ENV_FILE", "_REPO_ROOT"]
