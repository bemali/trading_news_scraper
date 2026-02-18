# Plan

## Learning Notes
- [docker-compose-learning.md](docker-compose-learning.md) for Docker Compose command and container wiring notes.

## Goals
- Run as an Azure Container Job.
- Local testing via Docker Compose.
- Use Azure AI endpoint for analysis.
- Use external News API with key stored in Azure Key Vault.
- Store results in PostgreSQL.
- Source code lives in `src/`.

## Desired Architecture (High Level)
- **Orchestrator**: `src/pipeline.py` (or equivalent entrypoint) runs the job.
- **News Fetch**: calls external News API, based on configured query/spec.
- **AI Analysis**: calls Azure AI endpoint with fetched news content.
- **Persistence**: writes analysis output to PostgreSQL.
- **Secrets**: News API key and DB creds pulled from Azure Key Vault at runtime.
- **Deployment**: container image built and deployed to Azure Container Jobs.
 - **Config**: non-secrets in `settings.json`, secrets in `.env` (or Key Vault in Azure).

## Local Development & Testing
1. **Configure env vars**
   - **Secrets (.env)**:
     - `NEWS_API_KEY`
     - `AZURE_OPENAI_API_KEY`
     - `POSTGRES_CONN_STR`
   - **Non-secrets (settings.json)**:
     - `NEWS_API_BASE_URL`
     - `NEWS_API_CATEGORIES`
     - `NEWS_API_LIMIT`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_OPENAI_DEPLOYMENT`
     - `AZURE_OPENAI_API_VERSION`
     - `POSTGRES_INIT_SCHEMA`
2. **Run locally**
   - `docker compose up -d postgres`
   - `docker compose run --rm news_job`
3. **Validate**
   - Verify news fetch logs
   - Verify AI analysis output
   - Check rows in PostgreSQL

## Implementation Steps (Repo)
1. **Review existing code**
   - `src/ai_analysis.py` for Azure AI integration.
   - `scripts/test_fetch_news.py` for News API logic.
   - `migrations/001_create_tables.sql` for schema.
2. **Fill in missing pieces**
   - Standardize config loading (env vars -> config object).
   - Create `src/news_fetcher.py` to wrap the News API call.
   - Create `src/db.py` to manage PostgreSQL connection + inserts.
   - Add an orchestrator `src/pipeline.py` to wire fetch -> analyze -> store.
3. **Logging & error handling**
   - Structured logs for each step.
   - Fail fast on missing config.
4. **Docker**
   - Ensure `Dockerfile` builds app with required dependencies.
   - Ensure `docker-compose.yml` includes app + PostgreSQL.

## Cloud Deployment (Azure)
1. **Container Registry**
   - Create or use existing Azure Container Registry (ACR).
   - Build and push image to ACR.
2. **Key Vault**
   - Store `NEWS_API_KEY`, `AZURE_OPENAI_API_KEY`, `POSTGRES_CONN_STR` in Key Vault.
   - Configure managed identity for Container Job.
3. **Azure Container Jobs**
   - Create Container Job pointing to ACR image.
   - Grant managed identity access to Key Vault.
   - Pass Key Vault secrets as env vars.
4. **Networking**
   - Ensure job can reach News API, Azure AI endpoint, and PostgreSQL.
5. **Monitoring**
   - Enable logs in Azure Monitor.
   - Optional: set alerting on job failures.

## Next Steps
- Confirm preferred News API provider and query spec.
- Decide job schedule (manual, cron, or event-driven).
- Validate AI analysis payload and output format.
- Finalize database schema for analysis results.

## Debug (Azure Container Jobs `ProcessExited`)
1. **Inspect job execution logs in Portal**
   - `Container Apps Jobs` -> job -> `Job executions` -> latest failed run -> `Logs`.
   - Capture first Python traceback and failing module/line.
2. **Stream logs during a manual rerun**
   - Trigger `Run now` and watch logs live.
   - Identify which stage fails: config load, Key Vault, OpenAI auth, DB connect, or insert.
3. **Verify required environment variables/secrets**
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_VERSION`
   - `POSTGRES_CONN_STR` (secret reference)
   - `AZURE_KEY_VAULT_URL`
   - `NEWS_API_KEY_SECRET_NAME`
   - Optional fallback: `AZURE_OPENAI_API_KEY`, `NEWS_API_KEY`
4. **Validate managed identity + RBAC**
   - Job identity has `Key Vault Secrets User` on Key Vault.
   - Job identity has `Cognitive Services OpenAI User` on Azure OpenAI.
5. **Validate PostgreSQL access**
   - `POSTGRES_CONN_STR` includes `sslmode=require`.
   - DB user in connection string has write permissions on target tables.
   - Network path from Container Apps environment to PostgreSQL is allowed.
6. **Reproduce locally with same image/env**
   - `docker run --rm --env-file .env <image>:<tag>`
   - Compare traceback with Azure logs to isolate environment-specific issues.


