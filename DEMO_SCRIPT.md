# SporeLink Demo Video Script

A 5-10 minute recording guide. Uses **Windows PowerShell** commands.

## Preparation

1. Repository cloned and open in **PowerShell**
2. `.env` file ready (copy from `.env.example`, replace `change-me`)
3. Docker Desktop running
4. Browser tab open for Swagger

```powershell
cd ~/SporeLink
$env:API_KEY = "your-secret-api-key"
```

---

## 00:00 - 00:40 : Repository Structure

**PowerShell:**

```powershell
ls
```

**Say:**

> "This is SporeLink, an IoT telemetry service for Nova IoT mushroom cultivation controllers. The `app/` folder has our FastAPI application with four endpoints. `migrations/` has our SQL schema. `tests/` has 13 unit tests. `terraform/` has our Fly.io infrastructure. `scripts/` has backup and restore utilities."

**Show briefly:** Open `app/main.py` and scroll through it.

---

## 00:40 - 01:30 : Docker Compose Startup

**PowerShell:**

```powershell
docker compose up --build
```

**Say:**

> "One command starts everything. PostgreSQL starts first with a health check, then the migration container runs our SQL, then the API starts, then Nginx. Only port 80 is exposed. The API and database are on an internal Docker network."

**Wait** until API startup is visible, then:

```powershell
# Press Ctrl+C, then run in background:
docker compose up -d --build
docker compose logs -f api
```

Press Ctrl+C once the API is running.

---

## 01:30 - 02:30 : Swagger / API

**PowerShell:**

```powershell
docker compose ps
```

**Say:**

> "All four services are running. Postgres is healthy. Migration exited with code 0. Let me open the auto-generated Swagger documentation."

**Open** `http://localhost/docs` in your browser.

> "FastAPI generates this interactive documentation automatically. We can see all four endpoints, the required headers, and the validation rules. You can even test endpoints right here."

---

## 02:30 - 03:10 : Telemetry POST / Latest / History

**PowerShell:**

```powershell
Invoke-RestMethod -Method POST -Uri http://localhost/telemetry `
  -Headers @{"x-api-key"=$env:API_KEY; "Content-Type"="application/json"} `
  -Body '{"device_id":"nova-chamber-01","temperature":24.5,"humidity":82.3,"co2":612.0,"substrate_moisture":71.0}'

# Send a couple more
Invoke-RestMethod -Method POST -Uri http://localhost/telemetry `
  -Headers @{"x-api-key"=$env:API_KEY; "Content-Type"="application/json"} `
  -Body '{"device_id":"nova-chamber-01","temperature":24.8,"humidity":81.5,"co2":605.0,"substrate_moisture":70.2}'

# Get latest
Invoke-RestMethod -Uri http://localhost/devices/nova-chamber-01/latest `
  -Headers @{"x-api-key"=$env:API_KEY} | ConvertTo-Json

# Get history
Invoke-RestMethod -Uri "http://localhost/devices/nova-chamber-01/history?limit=5" `
  -Headers @{"x-api-key"=$env:API_KEY} | ConvertTo-Json
```

**Say:**

> "A Nova IoT controller sends readings like this every few minutes. We get a 201 response. The latest endpoint returns the most recent reading. The history endpoint returns paginated results with a limit of 100 max to prevent dumping the entire database."

---

## 03:10 - 03:50 : Health Check

**PowerShell:**

```powershell
(Invoke-WebRequest -Uri http://localhost/health).StatusCode
(Invoke-WebRequest -Uri http://localhost/health).Content
```

**Say:**

> "The health endpoint isn't a hardcoded 200. It actually opens a connection to PostgreSQL. If the database is up, we get 200. This is what Docker's HEALTHCHECK and Fly.io's monitoring use."

---

## 03:50 - 04:40 : GitHub Actions

**Open** your repository on GitHub, go to the Actions tab.

**Say:**

> "When we push to main, GitHub Actions runs our full pipeline. Ruff lints the Python code. pytest runs our 13 unit tests with mocked database connections. Trivy scans the Docker image for known vulnerabilities. If anything fails, the pipeline stops and nothing deploys."

---

## 04:40 - 05:20 : Security Scan / GHCR

**Click** into the Trivy scan step of the workflow run.

**Say:**

> "Trivy scans the exact Docker image we just built, tagged as `sporelink:test`. It checks against a database of known CVEs. Because we use python:3.12-slim and a non-root user, our attack surface is already small. If a HIGH or CRITICAL vulnerability is found, the pipeline fails and the image is never pushed to GHCR."

---

## 05:20 - 06:10 : Real Deployment (if applicable)

**PowerShell:**

```powershell
Invoke-RestMethod -Uri https://sporelink.fly.dev/health
```

**Say:**

> "After the pipeline pushes to GitHub Container Registry, `flyctl deploy` pulls the image to Fly.io. The health check passes, meaning PostgreSQL is connected. Fly.io provides HTTPS automatically."

---

## 06:10 - 07:00 : Logs

**PowerShell:**

```powershell
flyctl logs -a sporelink --last 20s
```

**Say:**

> "We can stream production logs with flyctl. Each line is structured JSON with a timestamp, level, and message. This format is easy to parse with tools like jq."

---

## 07:00 - 07:50 : Database Failure

**PowerShell:**

```powershell
# Stop PostgreSQL
docker compose stop postgres

# Health check should return 503
(Invoke-WebRequest -Uri http://localhost/health).StatusCode
# Expected: 503

# Try sending telemetry (should fail)
try { Invoke-RestMethod -Method POST -Uri http://localhost/telemetry `
  -Headers @{"x-api-key"=$env:API_KEY; "Content-Type"="application/json"} `
  -Body '{"device_id":"nova-chamber-01","temperature":25,"humidity":80,"co2":600,"substrate_moisture":70}' }
catch { $_.Exception.Response.StatusCode.value__ }
# Expected: 500

# Restart PostgreSQL
docker compose start postgres

# Wait, then verify recovery
Start-Sleep -Seconds 5
(Invoke-WebRequest -Uri http://localhost/health).StatusCode
# Expected: 200
```

**Say:**

> "When PostgreSQL stops, the API container stays running but the health check returns 503 because it actually tests database connectivity. Telemetry POSTs fail with a 500 error. When PostgreSQL comes back, the health check returns to 200 immediately."

---

## 07:50 - 08:30 : Recovery

**PowerShell:**

```powershell
# Kill the API container to simulate a crash
docker compose kill api

# Watch it restart automatically
docker compose logs --tail 10 api

# Verify recovery
docker compose ps api
(Invoke-WebRequest -Uri http://localhost/health).StatusCode
# Expected: 200
```

**Say:**

> "If the API container crashes, Docker automatically restarts it because of the `restart: unless-stopped` policy. There is a brief gap where requests fail, but the service comes back within seconds."

---

## 08:30 - 09:10 : Broken Deployment + Rollback

**Explain (do NOT run against production without reason):**

**Say:**

> "If a bad version gets through, every image pushed to GHCR is tagged with the commit SHA. To roll back, we deploy the previous known-good SHA tag."

```powershell
# Show the rollback command (explanation only):
flyctl deploy --image ghcr.io/<owner>/sporelink:<previous-sha>

# Verify
Invoke-RestMethod -Uri https://sporelink.fly.dev/health
flyctl logs -a sporelink --last 30s
```

> "The CI pipeline prevents most bad deploys by running tests and Trivy first. Fly.io also has automatic health-check-based rollback."

---

## 09:10 - 10:00 : Architecture + Secrets Explanation

**Say:**

> "Let me summarize the full architecture. IoT controllers send telemetry over HTTPS to Fly.io, which routes to our Nginx reverse proxy on port 80. Nginx forwards to FastAPI on port 8000, which validates with Pydantic and stores in PostgreSQL. The health check tests real database connectivity."

> "Security: our `.gitignore` excludes all `.env` files. The Dockerfile only copies `app/` and `migrations/` -- no secrets enter the image. Secrets are injected at runtime. On Fly.io, they're set with `flyctl secrets set` and stored encrypted by the platform. Terraform does not contain any secrets."

> "That's SporeLink. Thanks for watching."

---

## Recording Tips

- Use a large monospace font (at least 16pt) in PowerShell
- Dark terminal background with high-contrast text
- Pause after each command so the audience can read output
- Export at 1080p minimum, 30fps
- If you make a typo, re-record that segment