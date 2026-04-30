"""Load settings from environment (.env) — keys are optional until you use that datasource."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _env_file() -> Path:
    return _root() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Always point at project root; dotenv is optional if file is missing
        env_file=str(_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    eventregistry_api_key: str = Field(default="", validation_alias="EVENTREGISTRY_API_KEY")
    google_application_credentials: str = Field(
        default="", validation_alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    google_cloud_project: str = Field(default="", validation_alias="GOOGLE_CLOUD_PROJECT")
    youtube_data_api_key: str = Field(default="", validation_alias="YOUTUBE_DATA_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    sketch_engine_user: str = Field(default="", validation_alias="SKETCH_ENGINE_USER")
    sketch_engine_key: str = Field(default="", validation_alias="SKETCH_ENGINE_KEY")
    # Default corpus for `sketch-ping` (override for hrWac, e.g. from Sketch UI)
    sketch_default_corp: str = Field(
        default="preloaded/bnc2", validation_alias="SKETCH_DEFAULT_CORP"
    )

    pipeline_data_dir: Path = Field(
        default_factory=lambda: _root() / "data", validation_alias="PIPELINE_DATA_DIR"
    )

    @property
    def data_raw(self) -> Path:
        p = self.pipeline_data_dir / "raw"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_processed(self) -> Path:
        p = self.pipeline_data_dir / "processed"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def has_eventregistry(self) -> bool:
        return bool(self.eventregistry_api_key.strip())

    @property
    def has_gcp(self) -> bool:
        return bool(
            self.google_application_credentials.strip() or self.google_cloud_project.strip()
        )

    @property
    def has_sketch(self) -> bool:
        return bool(self.sketch_engine_user.strip() and self.sketch_engine_key.strip())


def get_settings() -> Settings:
    return Settings()
