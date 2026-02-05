CREATE TABLE IF NOT EXISTS news_summaries (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    summary TEXT NOT NULL
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
