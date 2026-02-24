import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv



try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient    

except ImportError:
    DefaultAzureCredential = None
    SecretClient = None


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
    postgres_host: str
    postgres_user: str
    postgres_password: str


def load_config() -> Config:
    load_dotenv(override=True)
    settings = _load_settings()
    news_api_key = _resolve_news_api_key(settings)
    print(f"Using NEWS_API_KEY: {'***' if news_api_key else '(not set)'}")
    return Config(
        news_api_key=news_api_key,
        news_api_base_url=_env_or_setting("NEWS_API_BASE_URL", settings, NEWS_API_BASE_URL_DEFAULT),
        news_api_categories=_env_or_setting("NEWS_API_CATEGORIES", settings, NEWS_API_CATEGORIES_DEFAULT),
        news_api_limit=_env_or_setting_int("NEWS_API_LIMIT", settings, NEWS_API_LIMIT_DEFAULT),
        azure_openai_endpoint=_env_or_setting("AZURE_OPENAI_ENDPOINT", settings, ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_deployment=_env_or_setting("AZURE_OPENAI_DEPLOYMENT", settings, ""),
        azure_openai_api_version=_env_or_setting(
            "AZURE_OPENAI_API_VERSION", settings, "2025-01-01-preview"
        ),
        postgres_conn_str=os.getenv("POSTGRES_CONN_STR", ""),
        postgres_init_schema=_env_or_setting_bool("POSTGRES_INIT_SCHEMA", settings, False),
        postgres_host=_env_or_setting("POSTGRES_HOST", settings, ""),
        postgres_user=os.getenv("POSTGRES_USER", ""),
        postgres_password=os.getenv("POSTGRES_PASSWORD",""),
    )


def _resolve_news_api_key(settings: Dict[str, Any]) -> str:
    key_vault_url = _env_or_setting("AZURE_KEY_VAULT_URL", settings, "")
    key_vault_secret_name = _env_or_setting("NEWS_API_KEY_SECRET_NAME", settings, "NEWS-API-KEY")
    env_key = os.getenv("NEWS_API_KEY", "")

    if key_vault_url and key_vault_secret_name:
        if DefaultAzureCredential is None or SecretClient is None:
            logging.warning(
                "azure-identity/azure-keyvault-secrets is not installed; falling back to NEWS_API_KEY from environment"
            )
            return env_key

        try:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            client = SecretClient(vault_url=key_vault_url, credential=credential)
            return client.get_secret(key_vault_secret_name).value or env_key
        except Exception:
            logging.exception("Failed to read NEWS_API_KEY from Key Vault; falling back to environment")

    return env_key


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


if __name__ == "__main__":
    config = load_config()
    print(config)
