# trading_news_scraper
Scraping app for top few stocks, macro economic news, and sector level news


# External tools used
- News API : https://www.thenewsapi.com/documentation

# CICD

1. Migrating to pyproject.toml 
If the Azure extension created a requirements.txt, you can import those dependencies into your uv project and then delete the legacy file: 
Import dependencies: Run `uv add -r requirements.txt` to move your requirements into pyproject.toml and generate a uv.lock file.
Delete requirements.txt: Once imported, you can safely remove the requirements.txt file. Azure's deployment tools now prioritize uv.lock if it is present. 

2. Deploying with uv
Azure's build system uses a specific hierarchy to determine which package manager to use: 
uv: Used if both pyproject.toml and uv.lock are present.
Poetry: Used if only pyproject.toml is present.
pip: Used if only requirements.txt is present. 
Important: Ensure you include the uv.lock file in your deployment package (or push it to your repository for remote builds) to trigger the uv build process.

3. Local Development & CI/CD
For local development and automated pipelines, you can maintain compatibility without manual syncing:
Local Execution: Use uv run func start to run your Azure Functions locally within your uv-managed environment.
Generating requirements (Legacy CI): If you must use a legacy pipeline that only supports requirements.txt, you can auto-generate it from uv using:
`uv export --format requirements-txt -o requirements.txt`.