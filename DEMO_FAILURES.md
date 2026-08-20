# SporeLink — Failure Scenario Demonstrations

This document provides exact commands to demonstrate failure handling during the demo video. Run these against a local Docker Compose stack.

## Prerequisites

```bash
docker compose up -d --build
# Wait for all services to be healthy
docker compose ps
# Verify API is working
curl -s http://localhost/health | python3 -m json.tool
```

---

## Scenario 1: API Container Crash

**What we test:** Docker's `restart: unless-stopped` policy automatically restarts a killed container.

### Commands

```bash
# Show the API container is running
docker compose ps api

# In one terminal, watch the logs
docker compose logs -f api

# In another terminal, kill the API container
docker compose kill api

# Watch the logs — you will see the container exit, then restart automatically
# After ~5 seconds, the API should be back
docker compose ps api

# Verify the API recovered
curl -s http://localhost/health
# Expected: {"status":"healthy","database":"connected"}
```

**What happens:** Docker restarts the API container within seconds. In-flight requests during the crash are dropped (return connection refused). Once restarted, the API reconnects to PostgreSQL and resumes serving.

**Recovery:** Automatic. No human intervention needed.

---

## Scenario 2: Database Outage

**What we test:** The `/health` endpoint returns 503 when PostgreSQL is unreachable, and recovers when PostgreSQL comes back.

### Commands

```bash
# First, confirm health is 200
curl -w '\nHTTP %{http_code}\n' http://localhost/health
# Expected: {"status":"healthy","database":"connected"}
#          HTTP 200

# Stop PostgreSQL
docker compose stop postgres

# Now check health — should return 503
curl -w '\nHTTP %{http_code}\n' http://localhost/health
# Expected: {"detail":"Database unavailable"}
#          HTTP 503

# Also try posting telemetry — will fail
curl -w '\nHTTP %{http_code}\n' -X POST http://localhost/telemetry \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test","temperature":25,"humidity":70,"co2":400,"substrate_moisture":65}'
# Expected: HTTP 500 (internal server error — cannot connect to DB)

# Restart PostgreSQL
docker compose start postgres

# Wait a few seconds for PostgreSQL to be ready, then check health again
curl -w '\nHTTP %{http_code}\n' http://localhost/health
# Expected: HTTP 200 (recovered)
```

**What happens:** The API container stays running but cannot process requests that need the database. The `/health` endpoint correctly reports 503. When PostgreSQL restarts, the API automatically reconnects on the next request.

**Recovery:** Semi-automatic. PostgreSQL needs `docker compose start postgres` if manually stopped. The API reconnects automatically.

---

## Scenario 3: Missing Environment Variable

**What we test:** The application fails clearly at startup when required configuration is missing.

### Commands

```bash
# Try running the API without API_KEY set
docker compose run --rm -e DATABASE_URL=postgresql://sporelink:change-me@postgres:5432/sporelink api python -c "from app.main import app"
# Expected output on stderr:
# FATAL: Required environment variable(s) not set: API_KEY
# (container exits with code 1)

# Try running without DATABASE_URL
docker compose run --rm -e API_KEY=test api python -c "from app.main import app"
# Expected output on stderr:
# FATAL: Required environment variable(s) not set: DATABASE_URL
# (container exits with code 1)
```

**What happens:** The application checks for `API_KEY` and `DATABASE_URL` at import time. If either is missing, it prints a clear FATAL message to stderr and exits with code 1. The container will not start.

**Recovery:** Manual. Fix the `.env` file or environment configuration and restart.

---

## Scenario 4: Broken Deployment / Rollback

**What we test:** Deploying a bad version, observing the failure, then rolling back to the previous known-good image.

This scenario requires a deployed Fly.io application. If you have not deployed to Fly.io yet, this can be demonstrated with local Docker images.

### Local Docker Demonstration

```bash
# Step 1: Tag the current working image as "good"
docker compose build api
docker tag sporelink-api sporelink-api:good

# Step 2: Verify the good image works
docker compose up -d api
curl -s http://localhost/health
# Expected: 200

# Step 3: Simulate a bad deployment by breaking the code temporarily
# (In the video, explain: "If I deployed a version with a syntax error...")
# For a real demo, you would push a broken commit to GitHub,
# watch the CI pipeline fail at the test or build stage,
# and the deployment step would never execute.

# Step 4: Show that CI catches the break
# The pipeline is designed so that:
#   - Lint failure → pipeline stops
#   - Test failure → pipeline stops
#   - Build failure → pipeline stops
#   - Deploy NEVER runs if earlier stages fail

# Step 5: Rollback to the good version
docker compose up -d --build api
curl -s http://localhost/health
# Expected: 200
```

### Fly.io Rollback (if deployed)

```bash
# Step 1: Find previous image SHA from GHCR
# Go to GitHub → Packages → sporelink → see image tags
# Or: gh api /user/packages/container/sporelink/versions

# Step 2: Deploy the previous known-good image
flyctl deploy --image ghcr.io/<owner>/sporelink:sha-<previous-good-commit>

# Step 3: Verify recovery
flyctl logs -a sporelink --last 5m
curl https://<app-name>.fly.dev/health

# Step 4: Fix the code and push a new commit
git revert <bad-commit>
git push origin main
```

**What happens:** The CI pipeline prevents broken code from being deployed. If a bad image does get deployed, the health check fails and Fly.io stops routing traffic to it. Rolling back means deploying a previously tagged, known-good image.

**Recovery:** Manual rollback to a previous image tag or commit SHA.
