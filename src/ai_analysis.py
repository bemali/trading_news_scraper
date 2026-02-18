import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from openai import AzureOpenAI
from openai import APIConnectionError, AuthenticationError
from pydantic import BaseModel, Field

from src.models import Article

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
except ImportError:
    DefaultAzureCredential = None
    get_bearer_token_provider = None

load_dotenv()

AZURE_OPENAI_API_VERSION_DEFAULT = "2024-02-15-preview"


class Sentiment(BaseModel):
    score: float = Field(ge=-1.0, le=1.0)
    intensity: str
    consensus_divergence: float = Field(ge=0.0, le=1.0)


class Catalyst(BaseModel):
    category: str
    type: str
    surprise_factor: float = Field(ge=0.0, le=1.0)
    is_priced_in: bool


class PrimaryEntity(BaseModel):
    ticker: str
    sentiment: Sentiment
    catalyst: Catalyst


class CompetitorImpact(BaseModel):
    ticker: str
    impact_direction: str
    correlation_strength: float = Field(ge=0.0, le=1.0)


class SupplyChainImpact(BaseModel):
    ticker: str
    relationship: str
    impact: str


class MarketNetworkEffects(BaseModel):
    competitors: List[CompetitorImpact]
    supply_chain: List[SupplyChainImpact]
    sub_sector_ripples: List[str]


class MacroIndicators(BaseModel):
    jevons_paradox_risk: float = Field(ge=0.0, le=1.0)
    valuation_pressure: str
    time_horizon: str


class AIConfidenceMetrics(BaseModel):
    source_reliability: float = Field(ge=0.0, le=1.0)
    historical_pattern_match: str


class AnalysisOutput(BaseModel):
    event_id: str
    timestamp: str
    primary_entity: PrimaryEntity
    market_network_effects: MarketNetworkEffects
    macro_indicators: MacroIndicators
    ai_confidence_metrics: AIConfidenceMetrics


@dataclass(frozen=True)
class AnalysisRequest:
    event_id: str
    timestamp: str
    headlines: str
    base_prompt: str


def _load_base_prompt() -> str:
    md_path = Path(__file__).resolve().parent / "base_prompt.md"
    if md_path.exists():
        return md_path.read_text(encoding="utf-8").strip()

    py_path = Path(__file__).resolve().parent / "base_prompt.py"
    if py_path.exists():
        return py_path.read_text(encoding="utf-8").strip()

    return (
        "Role: You are a Senior Quantitative Research Analyst specializing in Sentiment Analysis and "
        "Market Microstructure.\n"
        "Task: Analyze the provided news text to extract structured data for a high-frequency trading model.\n"
    )


def _format_headlines(articles: Iterable[Article]) -> str:
    lines = []
    for a in articles:
        lines.append(f"- {a.title} ({a.source})")
    return "\n".join(lines)


def _build_request(articles: Iterable[Article]) -> AnalysisRequest:
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    headlines = _format_headlines(articles)
    base_prompt = _load_base_prompt()
    return AnalysisRequest(
        event_id=event_id,
        timestamp=timestamp,
        headlines=headlines,
        base_prompt=base_prompt,
    )


def _build_user_message(req: AnalysisRequest) -> str:
    schema = (
        "{\n"
        '  "event_id": "uuid",\n'
        '  "timestamp": "2026-02-05T12:00:00Z",\n'
        '  "primary_entity": {\n'
        '    "ticker": "NVDA",\n'
        '    "sentiment": {\n'
        '      "score": -0.85,\n'
        '      "intensity": "high",\n'
        '      "consensus_divergence": 0.4\n'
        "    },\n"
        '    "catalyst": {\n'
        '      "category": "disruptive_innovation",\n'
        '      "type": "efficiency_breakthrough",\n'
        '      "surprise_factor": 0.9,\n'
        '      "is_priced_in": false\n'
        "    }\n"
        "  },\n"
        '  "market_network_effects": {\n'
        '    "competitors": [\n'
        '      { "ticker": "AMD", "impact_direction": "negative", "correlation_strength": 0.75 }\n'
        "    ],\n"
        '    "supply_chain": [\n'
        '      { "ticker": "ASML", "relationship": "upstream", "impact": "neutral_to_negative" }\n'
        "    ],\n"
        '    "sub_sector_ripples": ["AI_Infrastructure", "Hyperscale_Cloud"]\n'
        "  },\n"
        '  "macro_indicators": {\n'
        '    "jevons_paradox_risk": 0.8,\n'
        '    "valuation_pressure": "compression",\n'
        '    "time_horizon": "immediate_selloff_longterm_recovery"\n'
        "  },\n"
        '  "ai_confidence_metrics": {\n'
        '    "source_reliability": 0.95,\n'
        '    "historical_pattern_match": "deepseek_r1_jan2025"\n'
        "  }\n"
        "}"
    )

    return (
        f"{req.base_prompt}\n\n"
        "Output must be valid JSON and match this schema exactly (no extra keys):\n"
        f"{schema}\n\n"
        f"Use event_id: {req.event_id}\n"
        f"Use timestamp: {req.timestamp}\n\n"
        f"Headlines:\n{req.headlines}"
    )


def synthesize_structured_output(
    endpoint: str,
    api_key: str,
    deployment: str,
    articles: Iterable[Article],
    api_version: str = AZURE_OPENAI_API_VERSION_DEFAULT,
) -> AnalysisOutput:
    if not endpoint or not deployment:
        raise ValueError("AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_DEPLOYMENT is not set")

    req = _build_request(articles)

    response = _invoke_azure_openai(
        endpoint=endpoint,
        deployment=deployment,
        api_version=api_version,
        user_message=_build_user_message(req),
        api_key=api_key,
    )

    content = response.choices[0].message.content or ""
    data = json.loads(content)

    if "event_id" not in data:
        data["event_id"] = req.event_id
    if "timestamp" not in data:
        data["timestamp"] = req.timestamp

    return AnalysisOutput.model_validate(data)


def _invoke_azure_openai(
    endpoint: str,
    deployment: str,
    api_version: str,
    user_message: str,
    api_key: str,
):
    token_scope = "https://cognitiveservices.azure.com/.default"

    if DefaultAzureCredential is not None and get_bearer_token_provider is not None:
        try:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            token_provider = get_bearer_token_provider(credential, token_scope)
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                azure_ad_token_provider=token_provider,
                max_retries=3,
            )
            return _create_chat_completion(client, deployment, user_message)
        except (AuthenticationError, APIConnectionError, RuntimeError):
            logging.exception("Managed identity auth failed for Azure OpenAI; falling back to API key")
        except Exception:
            logging.exception("Unexpected failure using managed identity; falling back to API key")

    if not api_key:
        raise ValueError(
            "Managed identity auth failed and AZURE_OPENAI_API_KEY is not set. "
            "Set a valid key in .env for fallback."
        )

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        max_retries=3,
    )
    return _create_chat_completion(client, deployment, user_message)


def _create_chat_completion(client: AzureOpenAI, deployment: str, user_message: str):
    return client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a market news analyst."},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=900,
        response_format={"type": "json_object"},
    )
