import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.ai_analysis import AZURE_OPENAI_API_VERSION_DEFAULT


NEWS_API_BASE_URL_DEFAULT = "https://api.thenewsapi.com/v1/news/all"
NEWS_API_CATEGORIES_DEFAULT = "business,tech"
NEWS_API_LIMIT_DEFAULT = 50


@dataclass(frozen=True)
class Config:
    news_api_key: str
    news_api_base_url: str
    news_api_categories: str
    news_api_limit: int
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str
    azure_openai_api_version: str
    postgres_conn_str: str
    postgres_init_schema: bool


def load_config() -> Config:
    load_dotenv()
    settings = _load_settings()
    return Config(
        news_api_key=os.getenv("NEWS_API_KEY", ""),
        news_api_base_url=_env_or_setting("NEWS_API_BASE_URL", settings, NEWS_API_BASE_URL_DEFAULT),
        news_api_categories=_env_or_setting("NEWS_API_CATEGORIES", settings, NEWS_API_CATEGORIES_DEFAULT),
        news_api_limit=_env_or_setting_int("NEWS_API_LIMIT", settings, NEWS_API_LIMIT_DEFAULT),
        azure_openai_endpoint=_env_or_setting("AZURE_OPENAI_ENDPOINT", settings, ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=_env_or_setting("AZURE_OPENAI_DEPLOYMENT", settings, ""),
        azure_openai_api_version=_env_or_setting(
            "AZURE_OPENAI_API_VERSION", settings, AZURE_OPENAI_API_VERSION_DEFAULT
        ),
        postgres_conn_str=os.getenv("POSTGRES_CONN_STR", ""),
        postgres_init_schema=_env_or_setting_bool("POSTGRES_INIT_SCHEMA", settings, False),
    )


def _load_settings() -> Dict[str, Any]:
    settings_path = Path(__file__).resolve().parent.parent / "settings.json"
    if not settings_path.exists():
        return {}
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in settings.json: {exc}") from exc


def _env_or_setting(key: str, settings: Dict[str, Any], default: str) -> str:
    env_val = os.getenv(key)
    if env_val is not None and env_val != "":
        return env_val
    val = settings.get(key, default)
    return str(val) if val is not None else default


def _env_or_setting_int(key: str, settings: Dict[str, Any], default: int) -> int:
    env_val = os.getenv(key)
    if env_val is not None and env_val != "":
        return int(env_val)
    val = settings.get(key, default)
    return int(val)


def _env_or_setting_bool(key: str, settings: Dict[str, Any], default: bool) -> bool:
    env_val = os.getenv(key)
    if env_val is not None and env_val != "":
        return env_val.lower() in {"1", "true", "yes"}
    val = settings.get(key, default)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in {"1", "true", "yes"}
    return bool(val)
