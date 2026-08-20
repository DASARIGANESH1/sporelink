# SporeLink

IoT telemetry ingestion service for **Nova IoT** mushroom cultivation controllers.

## 1. Project Overview

SporeLink is a lightweight, production-grade HTTP API that receives, validates, and stores telemetry readings from Nova IoT mushroom cultivation controllers deployed in growing facilities.

Each controller periodically sends sensor data — temperature, humidity, CO₂ levels, and substrate moisture — to SporeLink, which persists it in PostgreSQL and serves it back via query endpoints. The service is designed to be small, secure, and deployable anywhere Docker runs.

**What this project includes:**

- A FastAPI application with four endpoints (ingest, latest reading, paginated history, health check)
- Pydantic request validation with sensor-appropriate range constraints
- PostgreSQL 16 storage with indexed schema and parameterized queries
- Multi-stage Docker build with a non-root runtime user
- Nginx reverse proxy for production traffic handling
- GitHub Actions CI/CD pipeline (lint, test, security scan, build, deploy)
- Terraform infrastructure-as-code for Fly.io deployment
- 13 unit tests with mocked database and a live smoke test script

## 2. Features

- **Telemetry ingestion** — Accept validated sensor readings via `POST /telemetry`
- **Latest reading** — Retrieve the most recent reading for any device via `GET /devices/{id}/latest`
- **Paginated history** — Query historical readings with `limit` and `offset` via `GET /devices/{id}/history`
- **Real health check** — `GET /health` actually tests PostgreSQL connectivity (returns 200 or 503)
- **API key authentication** — All endpoints (except `/health`) require a valid `x-api-key` header
- **Input validation** — Pydantic enforces temperature (-50 to 100°C), humidity (0–100%), CO₂ (0–10,000 ppm), and substrate moisture (0–100%)
- **Structured JSON logging** — All application logs are single-line JSON for easy parsing
- **Non-root Docker container** — The API runs as user `sporelink`, not root
- **Nginx reverse proxy** — Only Nginx is exposed to the host; the API and database are on an internal network
- **Automated migration** — SQL migrations run automatically on container startup before the API starts
- **Infrastructure as Code** — Terraform provisions Fly.io resources declaratively

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.12 | Application runtime |
| Web framework | FastAPI | 0.115.6 | HTTP API with auto-validation |
| Data validation | Pydantic | 2.10.4 | Request schema validation |
| Database driver | psycopg (binary) | 3.2.4 | PostgreSQL v3 client |
| ASGI server | Uvicorn | 0.34.0 | Serves the FastAPI app |
| Database | PostgreSQL | 16 (alpine) | Telemetry storage |
| Reverse proxy | Nginx | alpine | Traffic routing, single entry point |
| Containerization | Docker | — | Build and run all services |
| Linting | Ruff | 0.9.4 | Fast Python linter/formatter |
| Testing | pytest | 8.3.4 | Unit tests (13 tests) |
| HTTP test client | httpx | 0.28.1 | TestClient dependency |
| Security scanning | Trivy | — | Container image vulnerability scanner |
| CI/CD | GitHub Actions | — | Automated pipeline |
| Container registry | GHCR | — | Docker image storage |
| Hosting | Fly.io | — | Production deployment (free tier) |
| IaC | Terraform | ≥ 1.0 | Infrastructure provisioning |

## 4. Architecture Diagram

```
+----------+     +------------------+     +-------+     +------+     +--------+     +-------+
|          |     |                  |     |       |     |      |     |        |     |       |
| Developer|---->|  GitHub Actions  |---->| GHCR  |---->|Fly.io|---->| Nginx  |---->|FastAPI|
|          |     |                  |     |       |     |      |     |        |     |       |
+----------+     |  Lint (ruff)     |     +-------+     +------+     | :80    |     | :8000 |
                 |  Test (pytest)   |                                |        |     |       |
                 |  Scan (Trivy)    |                                |proxy to|     |       |
                 |  Build (Docker)  |                                |api:8000|     +---+---+
                 |  Push to GHCR    |                                +--------+       |       |
                 |  Deploy (flyctl)  |                                                 |       |
                 |  Health verify    |                                                 v       |
                 +------------------+                                            +----------+
                                                                               |PostgreSQL|
                                                                               |  :5432   |
                                                                               +----------+
```

**Flow:** Developer pushes code to GitHub → GitHub Actions runs lint, tests, and security scan → builds Docker image → pushes to GitHub Container Registry → deploys to Fly.io via `flyctl` → verifies health endpoint.

## 5. Prerequisites

- **Docker Desktop** (or Docker Engine + Compose plugin) — for running the full stack locally
- **Python 3.12** (optional) — only needed to run unit tests locally; not needed inside Docker
- **Git** — for version control and pushing to GitHub
- **Fly.io account + flyctl CLI** (optional) — only needed for production deployment
- **Terraform >= 1.0** (optional) — only needed to run `terraform validate` locally

## 6. Repository Structure

```
SporeLink/
├── app/
│   ├── __init__.py          # Package marker (empty)
│   ├── main.py              # FastAPI app, all 4 endpoints, middleware, logging
│   └── database.py          # psycopg connection helper
├── migrations/
│   └── 001_create_telemetry.sql  # CREATE TABLE + indexes for telemetry data
├── nginx/
│   └── nginx.conf           # Reverse proxy config (port 80 → api:8000)
├── scripts/
│   ├── backup.sh            # Database backup via pg_dump (from Docker container)
│   └── restore.sh           # Database restore via psql (with confirmation prompt)
├── tests/
│   ├── __init__.py          # Package marker (empty)
│   ├── conftest.py          # Sets env vars before app import so tests load
│   └── test_api.py          # 13 unit tests with mocked PostgreSQL
├── terraform/
│   ├── main.tf              # Fly.io app + machine resources
│   ├── variables.tf         # Parameterized inputs (fly_api_token, region, etc.)
│   ├── outputs.tf           # Outputs: app URL, machine ID, region
│   └── README.md            # Terraform-specific usage instructions
├── .env.example             # Template for environment variables (committed to Git)
├── .gitignore               # Excludes .env, __pycache__, .terraform, etc.
├── docker-compose.yml       # Orchestrates postgres, migration, api, nginx
├── Dockerfile               # Multi-stage build (builder → non-root runtime)
├── fly.toml                 # Fly.io deployment config (ports, health check path)
├── requirements.txt         # Pinned Python dependencies
├── smoke_test.sh            # Curl-based live integration test script
├── README.md                # This file
├── DEMO_SCRIPT.md           # Demo video recording guide (19-step sequence)
├── DEMO_FAILURES.md         # Failure scenario demonstrations with exact commands
└── AI_USAGE.md              # AI usage disclosure
```

## 6. Local Development Setup

**Prerequisites:** Docker and Docker Compose installed.

```bash
# 1. Clone the repository
git clone https://github.com/<owner>/SporeLink.git
cd SporeLink

# 2. Create your environment file from the template
cp .env.example .env

# 3. Edit .env — replace all "change-me" values with real ones
#    API_KEY=your-secret-api-key
#    DATABASE_URL=postgresql://sporelink:your-db-password@postgres:5432/sporelink
#    POSTGRES_DB=sporelink
#    POSTGRES_USER=sporelink
#    POSTGRES_PASSWORD=your-db-password

# 4. Start all services (postgres → migration → api → nginx)
docker compose up --build

# 5. Verify everything is running
curl http://localhost/health
# Expected: {"status":"healthy","database":"connected"}

# 6. Run the smoke test
chmod +x smoke_test.sh
API_KEY=your-secret-api-key ./smoke_test.sh
```

## 7. Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_KEY` | Secret key that IoT devices must send in the `x-api-key` header | `change-me` |
| `DATABASE_URL` | PostgreSQL connection string for the FastAPI app | `postgresql://sporelink:change-me@postgres:5432/sporelink` |
| `POSTGRES_DB` | Database name (used by the PostgreSQL container) | `sporelink` |
| `POSTGRES_USER` | Database user (used by the PostgreSQL container) | `sporelink` |
| `POSTGRES_PASSWORD` | Database password (used by the PostgreSQL container) | `change-me` |

**Where each is used:**

- `API_KEY` and `DATABASE_URL` are read by `app/main.py` at startup. The application exits with an error if either is missing.
- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are only used by the `postgres` container in Docker Compose to initialize the database.

## 8. Running with Docker Compose

**Architecture:**

```
Browser/Client
      │
      ▼
  Nginx (:80) ─── only port exposed to host
      │
      ▼ (proxy_pass to api:8000)
  FastAPI (:8000) ─── on internal network only
      │
      ▼ (psycopg connection)
  PostgreSQL (:5432) ─── on internal network only
```

Four services run together:

1. **postgres** — PostgreSQL 16 Alpine with a health check. Data persists in the `postgres_data` Docker volume. Not exposed outside the `internal` network.
2. **migration** — Uses the same `postgres:16-alpine` image to run `psql -f /migrations/001_create_telemetry.sql` against the database, then exits. Waits for postgres to be healthy first.
3. **api** — The FastAPI application, built from the multi-stage Dockerfile. Waits for migration to complete successfully. Restarts automatically with `unless-stopped`. Not exposed directly.
4. **nginx** — Nginx Alpine, listens on port 80 on the host, proxies all traffic to `api:8000` on the internal network.

**Commands:**

```bash
# Start everything in the foreground (see logs)
docker compose up --build

# Start in the background
docker compose up -d --build

# View logs
docker compose logs -f api

# Stop everything
docker compose down

# Stop and delete the database volume (wipes all data)
docker compose down -v
```

## 9. API Endpoints

| Method | Path | Auth | Description | Success | Errors |
|--------|------|------|-------------|---------|--------|
| `POST` | `/telemetry` | `x-api-key` required | Ingest a sensor reading | `201 Created` | `401`, `422`, `500` |
| `GET` | `/devices/{device_id}/latest` | `x-api-key` required | Most recent reading for a device | `200 OK` | `401`, `404` |
| `GET` | `/devices/{device_id}/history` | `x-api-key` required | Paginated history for a device | `200 OK` | `401`, `404`, `422` |
| `GET` | `/health` | None | Check DB connectivity | `200 OK` | `503` |

**Request body for `POST /telemetry`:**

```json
{
  "device_id": "dev-001",
  "temperature": 25.0,
  "humidity": 70.0,
  "co2": 400.0,
  "substrate_moisture": 65.0
}
```

**Validation rules:**

- `device_id`: string, 1–100 characters
- `temperature`: float, -50.0 to 100.0 °C
- `humidity`: float, 0.0 to 100.0 %
- `co2`: float, 0.0 to 10,000.0 ppm
- `substrate_moisture`: float, 0.0 to 100.0 %

## 10. Example API Requests

Set your API key first:

```bash
export API_KEY="your-secret-api-key"
```

**POST /telemetry** — Send a sensor reading:

```bash
curl -X POST http://localhost/telemetry \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "nova-chamber-01",
    "temperature": 24.5,
    "humidity": 82.3,
    "co2": 612.0,
    "substrate_moisture": 71.0
  }'
# Response (201): {"status":"ok","device_id":"nova-chamber-01"}
```

**GET /devices/{id}/latest** — Get the most recent reading:

```bash
curl http://localhost/devices/nova-chamber-01/latest \
  -H "x-api-key: $API_KEY"
# Response (200):
# {
#   "device_id": "nova-chamber-01",
#   "temperature": 24.5,
#   "humidity": 82.3,
#   "co2": 612.0,
#   "substrate_moisture": 71.0,
#   "created_at": "2025-01-15T10:30:00+00:00"
# }
```

**GET /devices/{id}/history** — Get paginated history:

```bash
curl "http://localhost/devices/nova-chamber-01/history?limit=5&offset=0" \
  -H "x-api-key: $API_KEY"
# Response (200):
# {
#   "device_id": "nova-chamber-01",
#   "count": 2,
#   "readings": [ ... ]
# }
```

**GET /health** — Check database connectivity:

```bash
curl http://localhost/health
# Response (200): {"status":"healthy","database":"connected"}
# Response (503 if DB is down): {"detail":"Database unavailable"}
```

**Swagger UI** — Interactive API documentation:

Open [http://localhost/docs](http://localhost/docs) in your browser.

## 11. Testing

### Unit Tests (pytest)

The 13 unit tests in `tests/test_api.py` use `unittest.mock` to mock `psycopg.connect` and `get_connection()`. This means **no real database is needed** to run them.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test
pytest tests/test_api.py::test_health_healthy -v
```

**What is tested:**

- Health check returns 200 when DB is reachable
- Health check returns 503 when DB is unreachable
- Missing `x-api-key` returns 401
- Wrong `x-api-key` returns 401
- Incomplete payload returns 422
- Out-of-range temperature returns 422
- Negative humidity returns 422
- Valid `POST /telemetry` returns 201 and commits
- `GET /latest` returns 200 with correct data
- `GET /latest` returns 404 for unknown device
- `GET /history` returns 200 with paginated data
- `GET /history` returns 404 for unknown device
- `GET /history` with `limit=200` returns 422 (max is 100)

### Smoke Tests (live)

`smoke_test.sh` tests against a **running** Docker container. It sends real HTTP requests through Nginx.

```bash
# Make executable
chmod +x smoke_test.sh

# Run against local Docker Compose
API_KEY=your-secret-api-key ./smoke_test.sh

# Run against a remote instance
API_KEY=your-secret-api-key ./smoke_test.sh https://sporelink.fly.dev
```

## 12. Docker Explanation

### Why Multi-Stage?

The Dockerfile has two stages:

1. **Builder stage** — Installs Python dependencies into `/root/.local` using `pip install --user`. This layer includes build tools that are only needed during installation.
2. **Runtime stage** — Copies only the installed packages from the builder. No build tools, no pip cache, no compiler. The result is a smaller, more secure image.

### Why `python:3.12-slim`?

- **Size:** ~150 MB vs ~1 GB for the full `python:3.12` image.
- **Security:** Fewer installed packages means a smaller attack surface.
- **Reproducibility:** Pinned to a specific major.minor version for consistent builds.

### Why Non-Root User?

The runtime container creates a dedicated `sporelink` user and group (`useradd -r -g sporelink`). The `USER sporelink` directive ensures the process runs without root privileges. If an attacker exploits a vulnerability in the application, they are confined to a non-root user with no write access outside `/app`.

### Why These ENV Variables?

- `PYTHONDONTWRITEBYTECODE=1` — Prevents Python from creating `.pyc` files, keeping the image clean.
- `PYTHONUNBUFFERED=1` — Ensures log output is written immediately (not buffered), which is critical for `docker compose logs` to show real-time output.

### What Gets Copied?

Only `app/` and `migrations/` are copied. **No `.env` files, no tests, no `.git` directory** make it into the image. Secrets are injected at runtime via environment variables.

## 13. GitHub Container Registry (GHCR)

The CI pipeline pushes Docker images to GitHub Container Registry after Trivy passes.

**Image path:** `ghcr.io/<owner>/sporelink`

**Tags:**
- `sha-<commit-sha>` — immutable, pinned to the exact commit
- `main` — tracks the latest main branch build

The Terraform `fly_machine` resource references `ghcr.io/<owner>/sporelink:main`. This means every successful CI run produces a deployable image, and Fly.io pulls it during `flyctl deploy`.

No extra credentials are needed for GHCR push — the pipeline uses the automatically-provided `GITHUB_TOKEN`.

## 14. CI/CD Explanation

The GitHub Actions pipeline (triggered on push to `main`) runs these stages in order:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Lint    │  │  Test    │  │ IaC Val  │
│ (ruff)   │  │ (pytest) │  │(terraform│
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     └──────────────┼──────────────┘
                    ▼
           ┌────────────────┐
           │  Docker Build  │
           │  (buildx+GHCR) │
           └───────┬────────┘
                   ▼
          ┌────────────────┐
          │ Trivy Image    │
          │ Scan (HIGH,CRIT)│
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │ Push to GHCR   │
          │ (sha + branch) │
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │ Deploy Fly.io  │
          │ (flyctl deploy)│
          └───────┬────────┘
                  ▼
          ┌────────────────┐
          │ Health Verify  │
          │ (curl /health) │
          └────────────────┘
```

| Stage | Tool | What It Does | Why It Matters |
|-------|------|-------------|----------------|
| **Lint** | Ruff | Checks Python code for style and logic errors | Catches bugs before they reach production |
| **Test** | pytest | Runs 13 unit tests with mocked database | Verifies all endpoints behave correctly |
| **Security Scan** | Trivy | Scans the Docker image for known vulnerabilities | Prevents shipping images with CVEs |
| **Build** | Docker | Builds the multi-stage Docker image | Creates the deployable artifact |
| **Push** | Docker + GHCR | Pushes the image to GitHub Container Registry | Stores the image for deployment |
| **Deploy** | flyctl | Deploys the image to Fly.io | Ships the new version to production |
| **Health Verify** | curl | Hits the `/health` endpoint on the live service | Confirms the deployment is actually working |

Each stage blocks the next. If linting fails, tests don't run. If tests fail, the image isn't built. This fail-fast approach prevents broken code from reaching production.

## 15. Security & Secrets

### Where Do Secrets Live?

| Environment | Storage | How Injected | In Git? |
|-------------|---------|-------------|---------|
| **Local dev** | `.env` file (root of project) | Docker Compose reads `.env` automatically | **No** — `.env` is in `.gitignore` |
| **CI/CD** | GitHub Secrets (repository settings) | Referenced as `${{ secrets.NAME }}` in workflow | **No** — never stored in code |
| **Production (Fly.io)** | Fly.io Secrets | Set via `flyctl secrets set KEY=VALUE` | **No** — stored encrypted on Fly.io |

### Key Principles

- **No secrets in Git.** The `.gitignore` file excludes `.env` and `.env.*` (except `.env.example`).
- **No secrets in Docker images.** The Dockerfile only copies `app/` and `migrations/`. Environment variables are injected at container start time.
- **No secrets in logs.** The application logs structured JSON messages but never logs `API_KEY`, `DATABASE_URL`, or request headers.
- **API key validation.** Every endpoint (except `/health`) requires a matching `x-api-key` header. Mismatched or missing keys return 401.
- **Parameterized queries.** All SQL queries use `%s` placeholders via psycopg, preventing SQL injection.

## 16. Secrets Management

SporeLink never stores real credentials in source code, Docker images, or Terraform state.

**Local development:**
- Copy `.env.example` to `.env` and replace `change-me` with real values
- The `.env` file is excluded from Git by `.gitignore`
- Docker Compose reads `.env` automatically and injects variables into containers

**CI/CD (GitHub Actions):**
- `FLY_API_TOKEN` — stored as a GitHub Secret, referenced as `${{ secrets.FLY_API_TOKEN }}`
- `GITHUB_TOKEN` — automatically provided by GitHub, used for GHCR authentication
- `FLY_APP_HOSTNAME` — stored as a GitHub Variable, referenced as `${{ vars.FLY_APP_HOSTNAME }}`

**Production (Fly.io):**
- Set via `flyctl secrets set API_KEY=...` and `flyctl secrets set DATABASE_URL=...`
- Stored encrypted at rest on Fly.io's infrastructure
- Injected as environment variables at container start
- Never visible in `flyctl logs`, Terraform state, or the Docker image

## 17. Deployment

### Why Fly.io?

Fly.io was chosen because:

- **Free tier** includes enough resources for a small IoT service
- **Docker-native** — deploys containers directly, no platform-specific build step
- **Global edge network** — can deploy close to IoT devices (default region: `bom` / Mumbai)
- **Built-in health checks** — Fly.io proxies traffic away from unhealthy machines
- **Simple CLI** — `flyctl deploy`, `flyctl logs`, `flyctl secrets set`

### Alternatives Considered

| Platform | Why Not Chosen |
|----------|---------------|
| **Render** | Free tier spins down after inactivity — IoT devices send data 24/7 |
| **Railway** | Generous free tier but less predictable pricing at scale |

### How Deployment Works

1. GitHub Actions builds the Docker image and pushes it to GHCR
2. The pipeline runs `flyctl deploy` which tells Fly.io to pull the image and start a machine
3. Fly.io runs the Dockerfile's HEALTHCHECK (hits `/health` every 30s)
4. If health checks fail, Fly.io stops routing traffic to that machine

### Useful Commands

```bash
# View live logs
flyctl logs -a sporelink

# Restart the machine
flyctl machine restart <machine-id>

# Set a secret (replace with your real values)
flyctl secrets set API_KEY=change-me
flyctl secrets set DATABASE_URL=postgresql://sporelink:change-me@host:5432/sporelink

# List current secrets (values hidden)
flyctl secrets list

# Check machine status
flyctl machines list -a sporelink
```

## 18. Terraform / IaC

### What It Provisions

The Terraform configuration in `terraform/` creates:

1. **`fly_app.sporelink`** — A Fly.io application named `sporelink` using Docker runtime
2. **`fly_machine.sporelink`** — A single Fly.io Machine (1 CPU, 256 MB RAM) in the configured region, pulling the image from GHCR, with HTTP health checks on `/health`

### How to Use

```bash
cd terraform

# Initialize (downloads the fly-apps/fly provider)
terraform init

# Set required variables
export TF_VAR_fly_api_token="fly-token-here"
export TF_VAR_github_owner="your-github-username"

# Plan what will be created
terraform plan

# Apply the configuration
terraform apply

# View outputs (app URL, machine ID, etc.)
terraform output
```

### State Handling

- **Current approach:** Local state (`terraform.tfstate`), which is `.gitignore`d for safety.
- **For teams:** Terraform Cloud or S3 + DynamoDB for remote state with locking would prevent concurrent modifications.

## 19. Observability / Logging

### Structured JSON Logs

All application logs use a JSON format:

```json
{"time":"2025-01-15 10:30:00,123","level":"INFO","message":"Telemetry stored for device=nova-chamber-01"}
```

This makes logs easy to parse with tools like `jq`, Datadog, or CloudWatch.

### No Secrets in Logs

The application logs only operation messages. `API_KEY`, `DATABASE_URL`, and request headers are never included in log output.

### Health Check

The `/health` endpoint performs a real PostgreSQL connection test (3-second timeout). It returns:

- `200` with `{"status":"healthy","database":"connected"}` when the database is reachable
- `503` with `{"detail":"Database unavailable"}` when it is not

This is used by Docker's HEALTHCHECK, Fly.io's http_checks, and monitoring tools.

### Platform Monitoring

- **Docker Compose:** Use `docker compose logs -f api` to tail logs locally
- **Fly.io:** Use `flyctl logs -a sporelink` to stream production logs
- **No metrics dashboard** is included in this version (see Known Limitations)

## 20. Failure Handling

### API Container Crashes

**What happens:** Docker's `restart: unless-stopped` policy automatically restarts the API container. There may be a brief period (a few seconds) where requests fail.

**Observe it:**

```bash
# Kill the API container
docker compose kill api

# Watch it restart
docker compose logs -f api

# Confirm recovery
curl http://localhost/health
```

### Database Outage

**What happens:** The `/health` endpoint returns 503. All telemetry POSTs and GETs fail with 500 or 503. The API container stays running but cannot process requests.

**Observe it:**

```bash
# Stop the PostgreSQL container
docker compose stop postgres

# Health check now returns 503
curl -w '\n%{http_code}\n' http://localhost/health
# Expected: {"detail":"Database unavailable"}
#          503

# Restart PostgreSQL
docker compose start postgres
```

### Missing Environment Variable

**What happens:** The application exits immediately at startup with a fatal error message. It will not start without `API_KEY` and `DATABASE_URL`.

**Observe it:**

```bash
# Remove a required variable and try to start
docker compose run --rm -e API_KEY= api python -c "from app.main import app"
# Expected output on stderr:
# FATAL: Required environment variable(s) not set: API_KEY, DATABASE_URL
```

### Broken Deployment

**What happens:** If a bad image is deployed to Fly.io, the health check will fail. Fly.io stops routing traffic to the unhealthy machine.

**Observe it:**

```bash
# Check machine status
flyctl machines list -a sporelink

# View recent logs for errors
flyctl logs -a sporelink
```

## 21. Recovery

| Failure | How It Recovers | Manual Step Needed? |
|---------|-----------------|---------------------|
| API container crash | Docker restarts automatically (`unless-stopped`) | No — automatic |
| Database outage | PostgreSQL restarts; API returns 503 until DB is back | `docker compose start postgres` if manually stopped |
| Missing env var | Application refuses to start | Fix `.env` and run `docker compose up --build api` |
| Bad deployment | Health check fails; Fly.io stops routing traffic | Rollback to previous image (see Rollback section) |
| Corrupted database volume | Data loss | Restore from backup (see Backup section) |

## 22. Backup & Restore

### What Gets Backed Up

The only persistent data is the `postgres_data` Docker volume, which contains all telemetry readings.

### Backup Procedure

```bash
# Create a SQL dump from the running PostgreSQL container
docker compose exec postgres pg_dump -U sporelink sporelink > backup_$(date +%Y%m%d_%H%M%S).sql
```

This produces a plain-text SQL file with all `INSERT` statements needed to recreate the data.

### Restore Procedure

```bash
# Option 1: Restore into a running container
docker compose exec -T postgres psql -U sporelink sporelink < backup_20250115_103000.sql

# Option 2: Restore into a fresh environment
docker compose down -v                              # Wipe everything
docker compose up -d postgres                      # Start fresh DB
# Wait for health check, then:
docker compose exec -T postgres psql -U sporelink sporelink < backup_20250115_103000.sql
docker compose up -d                               # Start migration + api + nginx
```

### RPO / RTO

- **RPO (Recovery Point Objective):** Depends on how often you run `pg_dump`. With daily dumps, up to 24 hours of data could be lost. For mushroom cultivation telemetry (readings every few minutes), this is acceptable.
- **RTO (Recovery Time Objective):** A few minutes — restore the SQL dump and restart services.

### Why Backup Is Not Replication

This project uses **backup (pg_dump)**, not **replication** (streaming replication, logical replication, etc.). Replication would provide real-time data copying to a standby server, but adds significant complexity. For a single-instance IoT telemetry service on the free tier, periodic backups are the right trade-off.

## 23. Rollback

If a bad deployment reaches production, you can roll back to any previously pushed Docker image.

### Step 1: Find the Previous Image

```bash
# List recent images in GHCR (via GitHub API or web UI)
# The image tag is the Git commit SHA, e.g.: ghcr.io/owner/sporelink:sha-abc1234
```

### Step 2: Deploy the Previous Image

```bash
# Deploy a specific image to Fly.io
flyctl deploy --image ghcr.io/<owner>/sporelink:sha-<previous-commit>
```

### Step 3: Verify

```bash
# Check health
curl https://sporelink.fly.dev/health

# Check logs
flyctl logs -a sporelink

# Check machine status
flyctl machines list -a sporelink
```

### Step 4 (Optional): Revert the Code

```bash
# On your local machine, revert the bad commit
git revert <bad-commit-sha>
git push origin main
```

## 24. Known Limitations

- **Single instance:** Only one Fly.io Machine is provisioned. No horizontal scaling or high availability.
- **Local Terraform state:** Uses local `terraform.tfstate` with no remote state backend or locking. Not safe for team collaboration.
- **No metrics dashboard:** No Prometheus, Grafana, or any time-series metrics collection.
- **No alerting:** No automated alerts for high error rates, latency, or disk usage.
- **No HTTPS on local:** Local Docker Compose uses HTTP on port 80. HTTPS is only provided by Fly.io's edge proxy in production.
- **No authentication rotation:** The API key is a single static secret. No key rotation mechanism or per-device keys.
- **No rate limiting:** Any valid API key can send unlimited requests. No protection against abuse or DDoS.
- **No data retention policy:** Telemetry data accumulates forever. No TTL or automatic cleanup.
- **No pagination metadata:** The history endpoint returns results but no total count or `next`/`prev` links.
- **No CORS configuration:** The API does not set CORS headers, so browser-based clients cannot call it directly.
- **Migration ordering:** Only one migration file exists. No migration framework (Alembic, etc.) for versioned, reversible migrations.
- **Connection per request:** Each API request opens and closes a database connection. No connection pooling.

## 25. AI Usage Disclosure

See [AI_USAGE.md](AI_USAGE.md) for a complete disclosure of AI tool usage during development.

## 26. Demo Instructions

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a step-by-step recording guide covering all major features, failure scenarios, and recovery procedures.
