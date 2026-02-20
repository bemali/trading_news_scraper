import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable

import psycopg2

from src.ai_analysis import AnalysisOutput
from src.models import Article


DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2


def _sleep_backoff(attempt: int, base_seconds: int) -> None:
    delay = base_seconds * (2 ** (attempt - 1))
    time.sleep(delay)


def _read_migration_sql() -> str:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    parts = []
    for path in sorted(migrations_dir.glob("*.sql")):
        parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n".join(p for p in parts if p)


def connect_postgres(conn_str: str):
    if conn_str and conn_str.strip():
        logging.info("Using Postgres connection source: POSTGRES_CONN_STR")
        return psycopg2.connect(conn_str.strip())

    host = os.getenv("POSTGRES_HOST", "").strip()
    user = os.getenv("POSTGRES_USER", "").strip()
    password = os.getenv("POSTGRES_PASSWORD", "").strip()
   

    missing = []
    if not host:
        missing.append("POSTGRES_HOST")
    if not user:
        missing.append("POSTGRES_USER")
    if not password:
        missing.append("POSTGRES_PASSWORD")
    if missing:
        raise ValueError(
            "Postgres configuration not set. Provide POSTGRES_CONN_STR, or set all of: "
            f"POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD. Missing: {', '.join(missing)}"
        )

    logging.info("Using Postgres connection source: POSTGRES_* fallback")

    print(user, password, host)
    cnx = psycopg2.connect(user=user, password=password, host=host, port=5432, database="news", sslmode="require")

    return cnx


def store_results(
    conn_str: str,
    analyses: Iterable[AnalysisOutput],
    articles: Iterable[Article],
    init_schema: bool,
) -> None:
    analysis_list = list(analyses)
    article_list = list(articles)
    if len(analysis_list) != len(article_list):
        raise ValueError(
            "Analyses/articles length mismatch: "
            f"{len(analysis_list)} analyses for {len(article_list)} articles"
        )

    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            with connect_postgres(conn_str) as conn:
                with conn.cursor() as cur:
                    if init_schema:
                        cur.execute(_read_migration_sql())

                    for analysis, article in zip(analysis_list, article_list):
                        payload = analysis.model_dump()
                        primary_entity = payload.get("primary_entity", {})
                        sentiment = primary_entity.get("sentiment", {}) if isinstance(primary_entity, dict) else {}
                        catalyst = primary_entity.get("catalyst", {}) if isinstance(primary_entity, dict) else {}
                        macro = payload.get("macro_indicators", {})
                        market_network = payload.get("market_network_effects", {})
                        sub_sector_ripples = market_network.get("sub_sector_ripples", [])
                        ai_confidence = payload.get("ai_confidence_metrics", {})

                        cur.execute(
                            """
                            INSERT INTO news_summaries(
                                event_id,
                                analysis_timestamp,
                                primary_entity_ticker,
                                primary_entity_sentiment_score,
                                primary_entity_sentiment_intensity,
                                primary_entity_sentiment_consensus_divergence,
                                primary_entity_catalyst_category,
                                primary_entity_catalyst_type,
                                primary_entity_catalyst_surprise_factor,
                                primary_entity_catalyst_is_priced_in,
                                macro_indicators_jevons_paradox_risk,
                                macro_indicators_valuation_pressure,
                                macro_indicators_time_horizon,
                                mne_sub_sector_ripples,
                                ai_confidence_metrics
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                            """,
                            (
                                payload.get("event_id"),
                                payload.get("timestamp"),
                                primary_entity.get("ticker") if isinstance(primary_entity, dict) else None,
                                sentiment.get("score") if isinstance(sentiment, dict) else None,
                                sentiment.get("intensity") if isinstance(sentiment, dict) else None,
                                sentiment.get("consensus_divergence") if isinstance(sentiment, dict) else None,
                                catalyst.get("category") if isinstance(catalyst, dict) else None,
                                catalyst.get("type") if isinstance(catalyst, dict) else None,
                                catalyst.get("surprise_factor") if isinstance(catalyst, dict) else None,
                                catalyst.get("is_priced_in") if isinstance(catalyst, dict) else None,
                                macro.get("jevons_paradox_risk") if isinstance(macro, dict) else None,
                                macro.get("valuation_pressure") if isinstance(macro, dict) else None,
                                macro.get("time_horizon") if isinstance(macro, dict) else None,
                                json.dumps(sub_sector_ripples),
                                json.dumps(ai_confidence),
                            ),
                        )
                        summary_id = cur.fetchone()[0]

                        competitors = market_network.get("competitors", []) if isinstance(market_network, dict) else []
                        for comp in competitors:
                            if not isinstance(comp, dict):
                                continue
                            cur.execute(
                                """
                                INSERT INTO news_competitor_impacts(
                                    summary_id,
                                    ticker,
                                    impact_direction,
                                    correlation_strength
                                )
                                VALUES (%s, %s, %s, %s)
                                """,
                                (
                                    summary_id,
                                    comp.get("ticker"),
                                    comp.get("impact_direction"),
                                    comp.get("correlation_strength"),
                                ),
                            )

                        supply_chain = market_network.get("supply_chain", []) if isinstance(market_network, dict) else []
                        for sc in supply_chain:
                            if not isinstance(sc, dict):
                                continue
                            cur.execute(
                                """
                                INSERT INTO news_supply_chain_impacts(
                                    summary_id,
                                    ticker,
                                    relationship,
                                    impact
                                )
                                VALUES (%s, %s, %s, %s)
                                """,
                                (
                                    summary_id,
                                    sc.get("ticker"),
                                    sc.get("relationship"),
                                    sc.get("impact"),
                                ),
                            )

                        cur.execute(
                            """
                            INSERT INTO news_articles(id, summary_id, title, url, source, published_at, raw)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                article.id,
                                summary_id,
                                article.title,
                                article.url,
                                article.source,
                                article.published_at or None,
                                json.dumps(article.raw),
                            ),
                        )
            break
        except psycopg2.Error:
            logging.exception("Postgres operation failed on attempt %s", attempt)
            if attempt >= DEFAULT_MAX_RETRIES:
                raise
            _sleep_backoff(attempt, DEFAULT_BACKOFF_SECONDS)
