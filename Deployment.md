# Azure Deployment Guide

This guide targets your current architecture: containerized scraper job + PostgreSQL storage, with downstream access from Azure ML Studio and local VS Code.

## 1) Reference Architecture

- `Azure Container Apps Job` (`aca-job-news-scraper-prod`) runs `python -m src.pipeline` on cron.
- `Azure Container Registry` (`acrnewsprod`) stores the image.
- `Azure Database for PostgreSQL Flexible Server` (`pgflex-news-prod`) stores operational and analytics data.
- Optional `Read Replica` (`pgflex-news-prod-ro`) serves Azure ML and external app read workloads.
- `Azure Key Vault` (`kv-news-prod`) stores `NEWS_API_KEY` (and optional fallback secrets).
- `Azure OpenAI` (`aoai-news-prod`) uses Microsoft Entra auth from managed identity.
- `Managed Identity` (system-assigned on Container Apps Job; system/user-assigned on AML compute and other apps).

## 2) Identity and Secret Strategy

### Container job (writer path)
- Primary auth: managed identity.
- Fallback auth: `.env` values (`AZURE_OPENAI_API_KEY`, `NEWS_API_KEY`) for local/dev.
- Key Vault:
  - Set `AZURE_KEY_VAULT_URL`.
  - Set `NEWS_API_KEY_SECRET_NAME` (defaults to `NEWS_API_KEY` in code).
  - Grant job identity role: `Key Vault Secrets User`.
- Azure OpenAI:
  - Grant job identity role: `Cognitive Services OpenAI User`.

### Database roles
- `mi_news_job_writer`: write to ingestion tables.
- `mi_aml_reader`: read-only on analytics schema/views.
- `mi_external_app_reader` or `mi_external_app_writer`: least privilege for second app.
- `entra_group_devs_reader`: local devs in VS Code with Entra login.

## 3) Network Security Baseline

- Prefer private networking:
  - Private endpoint + private DNS for PostgreSQL, Key Vault, Azure OpenAI.
  - Container Apps Environment integrated in VNet.
  - AML managed network/private outbound to PostgreSQL.
- If temporary public access is needed:
  - Restrict firewall IPs tightly.
  - Keep SSL required.
  - Remove public access after private path is validated.

## 4) App Configuration

Set these on the Container Apps Job:

- Required:
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_DEPLOYMENT`
  - `AZURE_OPENAI_API_VERSION`
  - `POSTGRES_CONN_STR`
- Optional (Key Vault path for news key):
  - `AZURE_KEY_VAULT_URL`
  - `NEWS_API_KEY_SECRET_NAME`
- Fallback-only:
  - `AZURE_OPENAI_API_KEY`
  - `NEWS_API_KEY`

## 5) Deployment Sequence

1. Build and push image to ACR.
2. Provision PostgreSQL Flexible Server (+ optional read replica).
3. Provision Key Vault, store `NEWS_API_KEY`.
4. Provision Azure OpenAI deployment.
5. Provision Container Apps Environment + scheduled job.
6. Enable system-assigned identity on job.
7. Assign RBAC:
   - Job MI -> `Key Vault Secrets User` on Key Vault.
   - Job MI -> `Cognitive Services OpenAI User` on Azure OpenAI.
8. Configure env vars and start with manual run.
9. Validate DB writes, then enable schedule.
10. Provision AML compute identity and grant read role to DB.

## 6) PostgreSQL Access for Azure ML + VS Code

### Schema pattern for stable downstream use
- `ingest` schema: raw/operational tables (`news_articles`, `news_summaries`, etc.).
- `analytics` schema: stable views/materialized views for ML and app consumption.

### Grant model (example)
```sql
-- Run as admin in postgres DB
CREATE SCHEMA IF NOT EXISTS analytics;

GRANT USAGE ON SCHEMA analytics TO mi_aml_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO mi_aml_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO mi_aml_reader;

GRANT USAGE ON SCHEMA analytics TO entra_group_devs_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO entra_group_devs_reader;
```

### Azure ML Studio
- Use AML compute managed identity.
- Connect with Entra token auth (no DB password in notebooks/jobs).
- Point read workloads to replica endpoint when possible.

### Local VS Code
- Developers authenticate with `az login`.
- Use Entra token-based connection to PostgreSQL.
- Avoid shared static DB passwords in local `.env`.

## 7) Operational Controls

- Enable diagnostic logs for Container Apps, Postgres, Key Vault.
- Alert on:
  - Job failures
  - DB connection failures
  - Replica lag
  - Secret access failures
- Rotate fallback API keys and keep them as break-glass only.

## 8) Repository Changes Implemented

- `src/ai_analysis.py`: managed identity auth to Azure OpenAI first; fallback to `AZURE_OPENAI_API_KEY`.
- `src/config.py`: tries Key Vault (managed identity) for `NEWS_API_KEY`; fallback to `.env`.
- `pyproject.toml` and `requirements.txt`: added Azure identity/key vault client dependencies.
