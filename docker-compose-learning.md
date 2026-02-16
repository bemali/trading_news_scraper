# Docker Compose Learning Notes

## Command: `docker compose run --rm news_job`

This command runs a one-off container for the `news_job` service defined in `docker-compose.yml`.

- `run`: starts a one-time container for a service.
- `--rm`: removes that container after it exits.
- `news_job`: the service name in Compose.

## What is the reference point?

The main reference point is the Compose project directory, usually the folder where you run the command.

In this project, that is:

`d:\Code-Projects\trading_news_scraper`

Compose reads `docker-compose.yml` from this project context (unless you pass a different file/path with flags).

## How Compose, Dockerfile, and code connect

1. Compose picks the service:
   - `services.news_job` in `docker-compose.yml`

2. Service defines build context:
   - `build: .` means build from the project root folder.

3. Dockerfile is selected:
   - Since no custom `dockerfile:` is provided, Compose uses `./Dockerfile`.

4. Dockerfile copies code into image:
   - `COPY . /app` copies repo files into the image at build time.

5. Container runs with service command:
   - In Compose: `command: ["python", "-m", "src.pipeline"]`
   - Container starts using that command.

## Build time vs run time

- Build time:
  - `Dockerfile` instructions run and create an image.
  - Your code gets baked into the image (`COPY . /app`).

- Run time:
  - `docker compose run` starts a container from that built image.
  - Environment variables from Compose are injected.

## Important detail in this repo

`news_job` does not have a bind mount (`volumes:`) for source code.

That means local code changes are not automatically reflected inside the container until you rebuild:

- `docker compose build news_job`
- or `docker compose run --build --rm news_job`

## Healthcheck line you highlighted

In `postgres` service:

`test: ["CMD-SHELL", "pg_isready -U news -d news"]`

This checks if Postgres is ready to accept connections.

Because `news_job` has:

- `depends_on` with `condition: service_healthy`

Compose waits for Postgres health to pass before starting `news_job`.
