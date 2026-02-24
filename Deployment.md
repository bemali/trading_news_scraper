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

  
  - `POSTGRES_USER` : as a secret
  - `POSTGRES_PASSWORD`: as a secret
  - `NEWS_API_KEY_SECRET_NAME` = NEWS-API-KEY (relevant name in the key vault)

- Optional (If not set, will be loaded with settings)
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_DEPLOYMENT`
  - `AZURE_OPENAI_API_VERSION`
  - `POSTGRES_HOST`

- Fallback-only:
  - `POSTGRES_CONN_STR`: as a secret
  - `AZURE_OPENAI_API_KEY`: as a secret
  - `NEWS_API_KEY`: as a secret

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

## 5.1) Build and Push Docker Image to ACR

Run from project root (`d:\Code-Projects\trading_news_scraper`).

### Option A: Build locally, push with Docker
```powershell
# Login
az login

# Set values
$RG = "rg-news-prod"
$ACR = "acrnewsrod"                       # registry name without .azurecr.io
$IMAGE = "trading-news-scraper"
$TAG = "v1" # increment if a new image is being pushed after fixing the code

# Resolve login server and authenticate Docker to ACR
$LOGIN_SERVER = az acr show -g $RG -n $ACR --query loginServer -o tsv
az acr login -n $ACR

# Build and push
#### standard
docker build -t "${LOGIN_SERVER}/${IMAGE}:${TAG}" .
#### with cache cleared
docker build --no-cache -t "${LOGIN_SERVER}/${IMAGE}:${TAG}" .
#### push
docker push "${LOGIN_SERVER}/${IMAGE}:${TAG}"
```

Verify pushed tag:
```powershell
az acr repository show-tags -n $ACR --repository $IMAGE -o table
```

### Option B: Build directly in ACR (no local Docker required)
```powershell
az login
$RG = "rg-news-prod"
$ACR = "acrnewsprod"
$IMAGE = "trading-news-scraper"
$TAG = "v1"

az acr build -r $ACR -t "${IMAGE}:${TAG}" .
```

Verify image:
```powershell
az acr repository show-tags -n $ACR --repository $IMAGE -o table
```

### Updating Container Apps Job image
- In Azure Portal:
  1. Open `Container Apps Jobs`.
  2. Select your job.
  3. Open `Container` settings.
  4. Set image to `<acr-name>.azurecr.io/trading-news-scraper:<tag>`.
  5. Save and run a manual execution (`Run now`) to validate.

## 6) Azure Portal (UI) Creation Steps

Use these steps if you want to provision everything from `portal.azure.com` instead of CLI.

### 6.1 Resource group and region
1. In Azure Portal, search `Resource groups` -> `Create`.
2. Name it (example: `rg-news-prod`) and choose a single region for all resources where possible.
3. Create the resource group first, then create all services inside it.

### 6.2 Azure Container Registry (ACR)
1. Search `Container registries` -> `Create`.
2. Select your subscription/resource group, set name (example: `acrnewsprod`), choose SKU `Standard`.
3. Create.
4. After create: open the registry -> `Access keys` and keep `Admin user` disabled for production.
5. Your image path will look like: `<acr-name>.azurecr.io/trading-news-scraper:<tag>`.

### 6.3 Azure Database for PostgreSQL Flexible Server
1. Search `Azure Database for PostgreSQL flexible servers` -> `Create`.
2. Deployment option: `Flexible server`.
3. Compute/storage: start with burstable or general purpose as needed.
4. Authentication:
   - Enable Microsoft Entra authentication.
   - Keep password auth only if you need temporary bootstrap access.
5. Networking:
   - Preferred: `Private access (VNet Integration)`.
   - Transitional: `Public access` + strict firewall rules.
6. Security:
   - Enforce SSL/TLS.
   - Enable Defender/monitoring options as required.
7. Create server and note FQDN for `POSTGRES_CONN_STR`.

### 6.3.1 Build `POSTGRES_CONN_STR` from PostgreSQL resource
Use Azure Portal values from your PostgreSQL Flexible Server:

1. Open your PostgreSQL server in Portal.
2. From `Overview`, copy:
   - Server name (example: `pgflex-news-prod`)
   - Host/FQDN (example: `pgflex-news-prod.postgres.database.azure.com`)
3. From your server/database setup, identify:
   - Database name (example: `news`)
   - Username (example: `news_user`)
   - Password (the one you created for that user)
4. Build connection string:
```text
postgresql://<username>@<server-name>:<password>@<host-fqdn>:5432/<database>?sslmode=require
```
Example:
```text
postgresql://news_user@pgflex-news-prod:YourPassword@pgflex-news-prod.postgres.database.azure.com:5432/news?sslmode=require
```

Notes:
- Keep `sslmode=require`.
- Store this as a secret, not as plain text in app settings.

### 6.4 Optional read replica (for AML + external app reads)
1. Open primary PostgreSQL server.
2. Go to `Replication` -> `Create replica`.
3. Place replica in same or nearby region based on latency.
4. Route read-heavy ML/app traffic to replica endpoint.

### 6.5 Azure Key Vault + secret
1. Search `Key vaults` -> `Create`.
2. Choose `RBAC permission model` (recommended for consistency).
3. After create: open vault -> `Secrets` -> `Generate/Import`.
4. Add secret:
   - Name: `NEWS_API_KEY` (or your chosen `NEWS_API_KEY_SECRET_NAME`)
   - Value: your News API key
5. Copy vault URI for `AZURE_KEY_VAULT_URL`.

### 6.6 Azure OpenAI resource + model deployment
1. Create/open your Azure OpenAI resource.
2. Go to `Model deployments` -> `Create new deployment`.
3. Deploy the chat model you want and note the deployment name for `AZURE_OPENAI_DEPLOYMENT`.
4. From `Keys and Endpoint`, copy endpoint for `AZURE_OPENAI_ENDPOINT`.
5. In production, rely on Entra auth via managed identity (API key only as fallback).

### 6.7 Container Apps Environment
1. Search `Container Apps Environments` -> `Create`.
2. Place it in same region/resource group.
3. For private topology, attach to your VNet/subnet during creation.
4. Create environment.

### 6.8 Container Apps Job (scheduled container)
1. Search `Container Apps Jobs` -> `Create`.
2. Basics:
   - Name: `aca-job-news-scraper-prod`
   - Select environment from step 6.7
3. Container:
   - Image source: ACR
   - Image: `<acr-name>.azurecr.io/trading-news-scraper:<tag>`
   - Command override: `python -m src.pipeline`
4. Trigger type:
   - Use `Schedule` and set cron expression.
5. Identity:
   - Turn on `System assigned managed identity`.
6. Secrets:
   - Add secret `postgres-conn-str` with the full PostgreSQL connection string from section `6.3.1`.
7. Environment variables:
   - `POSTGRES_CONN_STR` -> use `Secret reference` -> `postgres-conn-str`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_OPENAI_API_VERSION`
   - `AZURE_KEY_VAULT_URL`
   - `NEWS_API_KEY_SECRET_NAME` (optional if using default `NEWS_API_KEY`)
   - Optional fallback vars: `AZURE_OPENAI_API_KEY`, `NEWS_API_KEY`
8. Create job.

### 6.9 RBAC assignments in Portal
1. Open Key Vault -> `Access control (IAM)` -> `Add role assignment`.
2. Assign `Key Vault Secrets User` to the Container Apps Job managed identity.
3. Open Azure OpenAI resource -> `Access control (IAM)` -> `Add role assignment`.
4. Assign `Cognitive Services OpenAI User` to the same managed identity.
5. If PostgreSQL uses Entra principals, create/grant DB roles for AML/app/dev users as shown in section 7.

### 6.10 First-run validation in Portal
1. Open Container Apps Job -> `Run now`.
2. Open job execution logs and confirm:
   - News fetch succeeded.
   - Azure OpenAI call succeeded (managed identity path).
   - DB insert succeeded.
3. In PostgreSQL, verify new rows in `news_summaries` and `news_articles`.
4. Only after successful manual run, keep the schedule enabled.

### 6.11 DB write-access checklist for Container Job
Adding `POSTGRES_CONN_STR` is necessary, but write access depends on the PostgreSQL role/user inside that connection string.

1. Confirm connection string user
   - Example user in conn string: `news_user@pgflex-news-prod`
2. Connect to PostgreSQL as admin and grant privileges:
```sql
GRANT CONNECT ON DATABASE news TO news_user;
GRANT USAGE ON SCHEMA public TO news_user;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO news_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO news_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO news_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO news_user;
```
3. Validate network reachability
   - Ensure Container Apps environment can reach PostgreSQL (private endpoint/VNet or firewall rule).
4. Validate runtime
   - Run job manually (`Run now`) and inspect logs for successful inserts.
   - Confirm data exists in:
     - `news_summaries`
     - `news_articles`

## 7) PostgreSQL Access for Azure ML + VS Code

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

## 8) Operational Controls

- Enable diagnostic logs for Container Apps, Postgres, Key Vault.
- Alert on:
  - Job failures
  - DB connection failures
  - Replica lag
  - Secret access failures
- Rotate fallback API keys and keep them as break-glass only.

## 9) Repository Changes Implemented

- `src/ai_analysis.py`: managed identity auth to Azure OpenAI first; fallback to `AZURE_OPENAI_API_KEY`.
- `src/config.py`: tries Key Vault (managed identity) for `NEWS_API_KEY`; fallback to `.env`.
- `pyproject.toml` and `requirements.txt`: added Azure identity/key vault client dependencies.
