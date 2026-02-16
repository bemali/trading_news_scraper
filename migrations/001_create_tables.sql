CREATE TABLE IF NOT EXISTS news_summaries (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id TEXT,
    analysis_timestamp TIMESTAMPTZ,
    primary_entity_ticker TEXT,
    primary_entity_sentiment_score NUMERIC,
    primary_entity_sentiment_intensity TEXT,
    primary_entity_sentiment_consensus_divergence NUMERIC,
    primary_entity_catalyst_category TEXT,
    primary_entity_catalyst_type TEXT,
    primary_entity_catalyst_surprise_factor NUMERIC,
    primary_entity_catalyst_is_priced_in BOOLEAN,
    macro_indicators_jevons_paradox_risk NUMERIC,
    macro_indicators_valuation_pressure TEXT,
    macro_indicators_time_horizon TEXT,
    mne_sub_sector_ripples TEXT,
    ai_confidence_metrics TEXT
);

CREATE TABLE IF NOT EXISTS news_articles (
    id TEXT PRIMARY KEY,
    summary_id INTEGER NOT NULL REFERENCES news_summaries(id),
    title TEXT,
    url TEXT,
    source TEXT,
    published_at TIMESTAMPTZ,
    raw JSONB
);

CREATE TABLE IF NOT EXISTS news_competitor_impacts (
    id SERIAL PRIMARY KEY,
    summary_id INTEGER NOT NULL REFERENCES news_summaries(id),
    ticker TEXT,
    impact_direction TEXT,
    correlation_strength NUMERIC
);

CREATE TABLE IF NOT EXISTS news_supply_chain_impacts (
    id SERIAL PRIMARY KEY,
    summary_id INTEGER NOT NULL REFERENCES news_summaries(id),
    ticker TEXT,
    relationship TEXT,
    impact TEXT
);
