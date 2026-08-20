# SporeLink Interview Notes

Beginner-friendly, technically correct answers referencing the actual project.

---

### Q1: Why Docker?
**Answer:** Docker packages the FastAPI app, its Python 3.12 runtime, and all dependencies into a single image that runs identically on my laptop, in CI, and on Fly.io. Without Docker, a "works on my machine" problem could easily happen since SporeLink depends on specific versions of psycopg, FastAPI, and uvicorn. The Dockerfile pins python:3.12-slim and installs from a locked requirements.txt, so every environment gets the exact same binary.

### Q2: Why Docker Compose?
**Answer:** SporeLink needs four services working together: PostgreSQL 16, a one-shot migration container, the FastAPI API, and Nginx. Docker Compose defines all four in docker-compose.yml with their networks, volumes, and dependency order. The depends_on chain (postgres healthy, then migration completed_successfully, then api) means I can run one command and get a fully wired stack. I don't have to manually create networks, link containers, or remember startup order.

### Q3: Why Nginx?
**Answer:** Nginx sits in front of the FastAPI app as a reverse proxy, so IoT devices and load balancers talk to port 80 instead of directly to Uvicorn on port 8000. In production, this matters because Nginx handles TLS termination, rate limiting, and buffering slow clients. In our docker-compose setup, nginx.conf forwards all requests to the upstream api block and adds X-Real-IP and X-Forwarded-For headers so the app can see the original client IP. On Fly.io, Nginx is not used because Fly's edge handles that routing.

### Q4: Why PostgreSQL?
**Answer:** Telemetry data from mushroom cultivation controllers is relational by nature: each reading has a device_id, timestamped sensor values, and we query by device with ordering and pagination. PostgreSQL 16 handles that with indexes on device_id and created_at. The TIMESTAMPTZ type ensures timestamps are stored correctly across timezones, which matters for a global IoT deployment. The app connects using psycopg v3, which is the modern async-capable PostgreSQL driver for Python, not the legacy psycopg2.

### Q5: Why use migrations?
**Answer:** The telemetry table schema, including its indexes on device_id and created_at, is defined in migrations/001_create_telemetry.sql instead of being created ad-hoc. This means the schema is version-controlled, repeatable, and auditable. In docker-compose.yml, the migration service runs psql against that SQL file and must complete successfully before the API starts. If I later need to add a column or a new table, I create 002_add_something.sql and it runs in the same ordered fashion. No hand-executed SQL, no guessing what the current schema is.

### Q6: Why use environment variables?
**Answer:** The app reads DATABASE_URL and API_KEY from os.environ at startup, not from any config file baked into the image. This is critical because the same Docker image runs in local development with a localhost PostgreSQL URL and in production on Fly.io with a remote managed database URL. The app calls sys.exit(1) immediately if either variable is missing, which prevents a silent misconfiguration from reaching production. Docker Compose passes them from the .env file, and Fly.io injects them as encrypted secrets.

### Q7: Why should secrets not be in Git?
**Answer:** If API_KEY or the database password were committed, anyone with repo access could impersonate IoT devices or read all telemetry data. Git history is permanent, so even deleting the file later does not remove the secret from past commits. SporeLink uses .env.example with placeholder values for documentation and keeps the real .env in .gitignore. On Fly.io, secrets are set via flyctl secrets set and stored encrypted at rest, so they never appear in code or Terraform state.

### Q8: Why non-root container?
**Answer:** The Dockerfile creates a sporelink user and group with no login shell and runs USER sporelink before starting Uvicorn. If an attacker finds a vulnerability in the app, they are confined to that unprivileged user and cannot install packages, modify system files, or read other containers' data. This is a defense-in-depth measure. The WORKDIR and all copied files are chown'd to sporelink so the process has the permissions it needs and nothing more.

### Q9: Why multi-stage Docker?
**Answer:** The Dockerfile has a builder stage that runs pip install and a final stage that only copies the installed packages from /root/.local into the runtime image. This means the final image does not contain pip, build tools, or the requirements.txt file. The result is a smaller, leaner image with a reduced attack surface since build-time tools like compilers are not present for an attacker to exploit.

### Q10: Why slim image?
**Answer:** python:3.12-slim is roughly 150MB compared to the full python:3.12 image at around 1GB. The slim variant strips out man pages, documentation, and unnecessary system packages. Since SporeLink only needs the Python runtime and libpq5 for psycopg, there is no reason to ship an entire Debian development environment. Smaller images also pull faster during deployment, which matters in CI and when Fly.io needs to schedule the container.

### Q11: Why GHCR?
**Answer:** GitHub Container Registry stores the built Docker image at ghcr.io/{owner}/sporelink:main so that Fly.io can pull it during deployment. It is tightly integrated with GitHub Actions: the CI pipeline builds the image, logs in to GHCR with GITHUB_TOKEN (automatically provided), and pushes without any extra credentials. Terraform then references that same image path in the fly_machine resource. This keeps build, storage, and deployment on one platform.

### Q12: What does CI do?
**Answer:** The GitHub Actions CI pipeline runs on every push to main and does three things: runs ruff for linting and formatting, runs pytest against the 13 unit tests in tests/test_api.py, and builds the Docker image. If any step fails, the pipeline stops and the image is not pushed or deployed. This catches issues like broken syntax, failing tests, or Docker build errors before they reach any environment. The tests use mocked psycopg connections so they run in seconds without needing a real database.

### Q13: What does CD do?
**Answer:** After CI passes, the CD portion pushes the verified Docker image to GHCR and then deploys it to Fly.io using flyctl deploy --remote-only. Fly.io pulls the new image, replaces the running machine, and runs health checks against /health. If the health check fails, Fly.io rolls back to the previous image automatically. This means every commit that passes tests gets a fully automated path from code to running service.

### Q14: Why run tests before deployment?
**Answer:** Without the test gate, a commit that breaks the Pydantic validation, messes up a SQL query, or introduces an import error would ship straight to Fly.io. The 13 pytest tests verify health check behavior, API key enforcement, payload validation bounds, and successful CRUD operations. They caught real bugs during development, like the BaseHTTPMiddleware issue where raising HTTPException returned 500 instead of 401. Running tests in CI takes under a minute and prevents regressions from reaching users.

### Q15: Why Trivy?
**Answer:** Trivy scans the built Docker image for known CVEs in OS packages and Python dependencies before it gets pushed to GHCR. The python:3.12-slim base, libpq5, and every pip-installed package like FastAPI and psycopg are checked against Trivy's vulnerability database. This catches problems like an outdated urllib3 or a vulnerable system library. Scanning the image rather than the filesystem is important because the final multi-stage image is what actually runs in production, and it has a different set of packages than the build stage.

### Q16: What happens if DB goes down?
**Answer:** The /health endpoint calls psycopg.connect(DATABASE_URL, connect_timeout=3) and returns 503 with "Database unavailable" if the connection fails. On Fly.io, the http_check service configured in Terraform and fly.toml hits /health every 30 seconds with a 5-second timeout. If the health check fails repeatedly, Fly.io restarts the machine. In the local Docker Compose setup, the Docker HEALTHCHECK does the same thing every 30 seconds. The API key middleware always skips /health, so these probes work without authentication.

### Q17: Why does /health return 503?
**Answer:** A 503 Service Unavailable status code is the HTTP-standard way to say "this service exists but cannot handle requests right now." The /health endpoint does not return a hardcoded 200; it actually attempts a real psycopg connection to PostgreSQL with a 3-second timeout. If that fails, it raises HTTPException(status_code=503). This is important because load balancers and orchestrators like Docker and Fly.io use the status code to decide whether to route traffic to this instance or redirect to a healthy one.

### Q18: What happens if API container crashes?
**Answer:** Docker Compose has restart: unless-stopped on the api service, so Docker will automatically restart the container if it exits. On Fly.io, the platform monitors the machine and restarts it if it becomes unresponsive or exits. In both cases, the container will come back up, attempt to connect to PostgreSQL, and start serving requests again. If PostgreSQL itself is down when the API restarts, the health check will return 503 and the container will keep retrying until the database is available.

### Q19: How does restart policy work?
**Answer:** The restart: unless-stopped policy in docker-compose.yml tells Docker to always restart the api container if it stops, unless a human explicitly ran docker compose stop. This means the API survives crashes, OOM kills, and unexpected errors without manual intervention. It does not restart if you intentionally bring the stack down, which is the correct behavior for local development. On Fly.io, the platform handles restarts automatically regardless of this setting.

### Q20: What does Terraform provision?
**Answer:** The Terraform configuration in terraform/main.tf provisions a Fly.io application and a single Fly.io Machine with 1 CPU and 256MB of memory in the configured region. It sets up TCP ports 80 and 443 with HTTP and TLS handlers, and configures the same /health http_check that fly.toml defines. The machine image is pulled from GHCR. Runtime secrets like API_KEY and DATABASE_URL are NOT in Terraform; they are set separately via flyctl secrets set so they never appear in the Terraform state file.

### Q21: What happens during terraform destroy?
**Answer:** Running terraform destroy removes the Fly.io application and its machine, which deallocates the compute resources and releases the app name. Any data stored on the machine's ephemeral filesystem is lost. However, PostgreSQL is not managed by Terraform in this project, so the database and its telemetry data are unaffected. This is why the backup.sh script exists: to preserve data that lives outside of Terraform's lifecycle. After a destroy, running terraform apply again would provision a fresh machine that pulls the latest image from GHCR.

### Q22: How does rollback work?
**Answer:** On Fly.io, if a newly deployed image fails its /health checks, the platform automatically stops routing traffic to it and restarts the previous healthy image. This is configured through the http_checks block in both fly.toml and the Terraform fly_machine resource, which specify a 30-second check interval and a 10-second grace period. In GitHub Actions, the CI pipeline prevents bad code from being deployed in the first place by running tests and Trivy before pushing the image. Between the two, most issues are caught before they affect users.

### Q23: Why backup instead of relying only on replication?
**Answer:** Replication protects against hardware failure of a single database node, but it does not protect against logical errors like accidentally dropping the telemetry table, a bad migration that corrupts data, or a bug that writes invalid values. The backup.sh script runs pg_dump to create a point-in-time SQL snapshot that can be restored with scripts/restore.sh. I recommend running this via cron daily and keeping 30 days of backups. A backup gives you a known-good state to restore from that replication simply cannot provide.

### Q24: How would you scale this 10x?
**Answer:** Ten times the current load means more IoT devices sending telemetry and more queries for history and latest readings. I would add a connection pooler like PgBouncer between the API and PostgreSQL since psycopg opens a new connection per request right now. The telemetry table's indexes on device_id and created_at would need to be monitored for bloat. On Fly.io, I would increase the machine count and add a Fly Postgres cluster with read replicas for the GET endpoints. For the write-heavy /telemetry endpoint, I might consider batch inserts where devices buffer a few readings before sending them.

### Q25: What would you change for production?
**Answer:** I would add TLS termination with a real certificate instead of plain HTTP on port 80. The single DATABASE_URL connection would be replaced with a PgBouncer connection pool. I would add structured logging with correlation IDs so a device's request can be traced through logs. The Terraform state would move to Terraform Cloud or S3 with DynamoDB locking to prevent concurrent changes. I would also add rate limiting on the /telemetry endpoint, set up alerting on 503 health checks, and configure automated daily backups with the existing backup.sh script.

### Q26: Why did you use AI?
**Answer:** AI tools like ChatGPT, Claude, and GitHub Copilot helped with scaffolding initial code, debugging specific issues, and drafting documentation. The most valuable use was troubleshooting the BaseHTTPMiddleware bug where raising HTTPException(401) inside the middleware returned 500 instead of 401. AI identified this as a known Starlette issue and suggested returning JSONResponse directly, which is the fix in the current code. AI also helped with the psycopg cursor mocking pattern in tests, where __enter__ needed to return self rather than a child mock.

### Q27: Which parts did you personally validate?
**Answer:** I ran all 13 pytest unit tests and confirmed they pass. I ran ruff check and ruff format --check with zero errors. I ran smoke_test.sh against a live Docker Compose deployment and verified all five checks pass. I manually tested each endpoint with curl, including failure scenarios like missing the API key, sending out-of-range values, and querying a nonexistent device. I tested what happens when PostgreSQL is down and confirmed the 503 response. I reviewed the Docker container to confirm it runs as the non-root sporelink user and contains no secrets. I grepped the entire repository for accidentally committed credentials. I reviewed the Terraform configuration for correctness and verified it does not contain any secrets.
