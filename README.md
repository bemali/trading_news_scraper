# trading_news_scraper
Scraping app for top few stocks, macro economic news, and sector level news

# External tools used
- News API : https://www.thenewsapi.com/documentation

# Configuration
- Non-secret settings live in `settings.json`.
- Secrets live in `.env` and are loaded via `python-dotenv`.
- Environment variables override `settings.json` at runtime.

Required secrets in `.env`:
- `NEWS_API_KEY`
- `AZURE_OPENAI_API_KEY`
- `POSTGRES_CONN_STR`

Common non-secret settings in `settings.json`:
- `NEWS_API_BASE_URL`
- `NEWS_API_CATEGORIES`
- `NEWS_API_LIMIT`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `POSTGRES_INIT_SCHEMA`

# Local Deployment (Docker Compose)
1. Set secrets in `.env`.
2. Start Postgres:
```bash
docker compose up -d postgres
```
3. Run the job:
```bash
docker compose run --rm news_job
```
4. If you hit a `pg_hba.conf` auth error locally, reset local Postgres volume and rerun:
```bash
docker compose down -v
docker compose up -d postgres
docker compose run --rm news_job
```

Notes:
- Postgres from host machine: `postgresql://news:news@127.0.0.1:5432/news`
- Postgres from `news_job` container: `postgresql://news:news@postgres:5432/news`
- Tables are created on startup when `POSTGRES_INIT_SCHEMA=true`.

# Viewing Results in VS Code (PostgreSQL SQL Explorer by Chris Kolkman)
1. Install extension: `PostgreSQL SQL Explorer` (publisher: Chris Kolkman).
2. Add a connection using:
- Host: `127.0.0.1`
- Port: `5432`
- Database: `news`
- Username: `news`
- Password: `news`
3. Connect and run queries, for example:
```sql
SELECT * FROM news_summaries ORDER BY id DESC LIMIT 20;
SELECT * FROM news_articles ORDER BY published_at DESC NULLS LAST LIMIT 20;
```

# Stopping Local Services
- Stop running services but keep containers/volumes:
```bash
docker compose stop
```
- Stop and remove containers/network (keep volumes/data):
```bash
docker compose down
```
- Stop and remove containers/network/volumes (deletes local Postgres data):
```bash
docker compose down -v
```

# Deployment Note
- This project is intended to run as a containerized job (e.g., Azure Container Apps Jobs).
- Configure the job schedule (cron) in your container job definition.

# CICD

1. Migrating to `pyproject.toml`
If a tool created a `requirements.txt`, you can import those dependencies into your uv project and then delete the legacy file:
Import dependencies: Run `uv add -r requirements.txt` to move your requirements into `pyproject.toml` and generate a `uv.lock` file.
Delete requirements.txt: Once imported, you can safely remove the `requirements.txt` file if your build uses uv.

2. Building containers with uv or pip
Choose one dependency source for your container build:
uv: Use `pyproject.toml` + `uv.lock` and install with uv in the Dockerfile.
pip: Use `requirements.txt` and install with pip in the Dockerfile.

3. Local Development & CI/CD
For local development and automated pipelines, you can maintain compatibility without manual syncing:
Generating requirements (Legacy CI): If you must use a legacy pipeline that only supports `requirements.txt`, you can auto-generate it from uv using:
`uv export --format requirements-txt -o requirements.txt`.
