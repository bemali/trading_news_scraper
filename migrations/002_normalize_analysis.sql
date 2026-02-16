ALTER TABLE news_summaries
    ADD COLUMN IF NOT EXISTS event_id TEXT,
    ADD COLUMN IF NOT EXISTS analysis_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS primary_entity_ticker TEXT,
    ADD COLUMN IF NOT EXISTS primary_entity_sentiment_score NUMERIC,
    ADD COLUMN IF NOT EXISTS primary_entity_sentiment_intensity TEXT,
    ADD COLUMN IF NOT EXISTS primary_entity_sentiment_consensus_divergence NUMERIC,
    ADD COLUMN IF NOT EXISTS primary_entity_catalyst_category TEXT,
    ADD COLUMN IF NOT EXISTS primary_entity_catalyst_type TEXT,
    ADD COLUMN IF NOT EXISTS primary_entity_catalyst_surprise_factor NUMERIC,
    ADD COLUMN IF NOT EXISTS primary_entity_catalyst_is_priced_in BOOLEAN,
    ADD COLUMN IF NOT EXISTS macro_indicators_jevons_paradox_risk NUMERIC,
    ADD COLUMN IF NOT EXISTS macro_indicators_valuation_pressure TEXT,
    ADD COLUMN IF NOT EXISTS macro_indicators_time_horizon TEXT,
    ADD COLUMN IF NOT EXISTS mne_sub_sector_ripples TEXT,
    ADD COLUMN IF NOT EXISTS ai_confidence_metrics TEXT;

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
