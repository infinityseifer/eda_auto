# app/core/config.py
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

# toml loader (py311+ has tomllib)
try:
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    import tomli as tomllib  # type: ignore


class TOMLSettingsSource(PydanticBaseSettingsSource):
    """
    Read app_settings.toml and emit a flat dict of Settings fields.
    Implements both __call__ and get_field_value (required in v2).
    Also normalizes common lowercase keys to match our Settings fields.
    """

    def __init__(self, settings_cls, file_path: str = "app_settings.toml"):
        super().__init__(settings_cls)
        self.file_path = file_path
        self._cache: dict[str, Any] | None = None

    def _load_raw(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache
        data: dict[str, Any] = {}
        if os.path.exists(self.file_path):
            with open(self.file_path, "rb") as f:
                raw = tomllib.load(f)

            # Merge known sections
            for section in ("app", "db", "queue", "cors"):
                sec = raw.get(section, {})
                if isinstance(sec, dict):
                    data.update(sec)

            # Allow top-level simple scalars too
            for k, v in raw.items():
                if isinstance(v, (str, int, float, bool)):
                    data[k] = v

        self._cache = data
        return data

    def __call__(self) -> dict[str, Any]:
        raw = self._load_raw()

        # Map common lowercase keys -> our Settings field names
        mapping = {
            "app_name": "APP_NAME",
            "api_version": "API_VERSION",
            "app_env": "APP_ENV",
            "storage_dir": "STORAGE_DIR",
            "database_url": "DATABASE_URL",
            "use_redis": "USE_REDIS",
            "redis_url": "REDIS_URL",
            "cors_origins": "CORS_ORIGINS",
            "origins": "CORS_ORIGINS",
        }

        out: dict[str, Any] = {}
        for k, v in raw.items():
            key = mapping.get(k, k)  # normalize if needed
            if key in {
                "APP_NAME",
                "API_VERSION",
                "APP_ENV",
                "STORAGE_DIR",
                "DATABASE_URL",
                "USE_REDIS",
                "REDIS_URL",
                "CORS_ORIGINS",
            }:
                out[key] = v
        return out

    def get_field_value(self, field, field_name):
        """
        Optional field-by-field fetch. We can reuse the flat dict we return
        from __call__ so pydantic-settings can ask for individual fields.
        """
        blob = self()
        key = field.alias or field_name
        if key in blob:
            return blob[key], field, field_name
        # also accept UPPERCASE in TOML (already handled in __call__, but safe)
        if key.upper() in blob:
            return blob[key.upper()], field, field_name
        return None, field, field_name


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = Field("Auto EDA & Storytelling")
    API_VERSION: str = Field("0.1.0")
    APP_ENV: str = Field("dev")

    # --- Storage ---
    STORAGE_DIR: str = Field("storage")

    # --- DB / Queue ---
    DATABASE_URL: str = Field("sqlite:///./dev.db")
    USE_REDIS: bool = Field(False)
    REDIS_URL: str = Field("redis://localhost:6379/0")

    # --- CORS ---
    CORS_ORIGINS: str = Field("http://127.0.0.1:8501,http://localhost:8501")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Load order: init kwargs -> TOML -> .env -> OS env -> secrets
        toml_source = TOMLSettingsSource(settings_cls, file_path="app_settings.toml")
        return (init_settings, toml_source, dotenv_settings, env_settings, file_secret_settings)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
