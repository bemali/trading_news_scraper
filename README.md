# trading_news_scraper
Scraping app for top few stocks, macro economic news, and sector level news


# External tools used
- News API : https://www.thenewsapi.com/documentation

# Local Testing (Docker)
1. Start dependencies (Postgres):
```
docker compose up -d postgres
```
2. Set secrets in `.env` (for Docker Compose) or export them in your shell.
3. Run the job locally:
```
docker compose run --rm news_job
```

Notes:
- Postgres is available at `postgresql://news:news@127.0.0.1:5432/news` from your host, and `postgresql://news:news@postgres:5432/news` from the `news_job` container.
- Tables are created on startup when `POSTGRES_INIT_SCHEMA=true`.

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
