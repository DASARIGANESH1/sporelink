# AI Usage Disclosure

## Summary

AI assistants were used during the development of SporeLink. This document discloses where and how.

## What AI Tools Were Used

| Tool | Usage |
|------|-------|
| **ChatGPT** (OpenAI) | Code scaffolding, debugging assistance, documentation drafting |
| **Claude** (Anthropic) | Code scaffolding, debugging assistance, documentation drafting |
| **GitHub Copilot** | Code scaffolding, CI/CD configuration, Terraform syntax |

## How AI Was Used

### Code Scaffolding

AI tools helped generate initial drafts of application code, Docker configurations, and CI/CD workflow files. For example, when I was setting up the GitHub Actions pipeline, I asked: _"how do I run Trivy against a Docker image that was just built with buildx, not against the filesystem?"_ The AI suggested using `load: true` in the build step and then referencing the image by tag in the Trivy action. I then verified this worked by reading the Trivy action documentation.

### Debugging Assistance

AI tools were consulted to troubleshoot specific issues:

- **BaseHTTPMiddleware + HTTPException:** I encountered a bug where raising `HTTPException(401)` inside `BaseHTTPMiddleware` caused unhandled 500 errors instead of 401 responses. I asked AI about this and learned it's a known issue in recent Starlette versions — the exception isn't caught by the middleware wrapper. The fix was to return a `JSONResponse(status_code=401)` directly instead of raising an exception.

- **pytest cursor mocking:** When my mocked psycopg connections weren't working, I discovered that `MagicMock.__enter__()` creates a child mock rather than returning the mock itself. AI helped me understand that psycopg's cursor context manager returns `self` on `__enter__`, so I needed to explicitly set `cursor_mock.__enter__ = MagicMock(return_value=cursor_mock)`.

### Documentation Assistance

AI tools assisted in drafting and structuring project documentation, including the README sections on Docker multi-stage builds, CI/CD pipeline explanation, and security architecture.

### CI/CD Configuration

AI tools provided guidance on GitHub Actions syntax, Trivy integration, and Fly.io deployment commands. For example: _"what's the correct way to pass a built Docker image to Trivy in GitHub Actions?"_ and _"how do I configure flyctl deploy --remote-only in CI?"_

## What AI Did NOT Do

- AI did not make architectural decisions (I chose the tech stack and deployment strategy)
- AI did not test or verify the code (I ran all 13 pytest tests and manual smoke tests)
- AI did not write the final versions of any file without my review
- AI did not deploy anything (all deployment was manual via flyctl)
- AI did not create the `.env` file or set any real credentials

## Authorship and Understanding

The author of this project understands every component of SporeLink and can explain, modify, and troubleshoot all parts independently. AI tools were used as development aids, not as replacements for understanding. Every line of code in this repository was reviewed and accepted by the author.

Specific things the author can explain without AI:

- Why `psycopg.connect()` is used instead of `psycopg2` (async-ready, v3 binary package, context manager support)
- Why the Dockerfile has two stages and what each layer contains
- Why the health check uses a 3-second `connect_timeout` and returns 503 on failure
- Why the migration runs as a separate `service_completed_successfully` container
- Why `x-api-key` middleware skips `/health` (so Docker and Fly.io health probes work without auth)
- Why Trivy scans the built image, not the filesystem
- How the `_mock_connection()` helper function works and why it's needed

## Verification

All code was verified by:

- Running the 13 pytest unit tests (all passing)
- Running `ruff check` and `ruff format --check` (zero errors)
- Running `smoke_test.sh` against a live Docker Compose deployment
- Manual testing of each API endpoint via curl
- Manual testing of failure scenarios (DB outage, missing env vars, container crash)
- Reviewing Docker container security (non-root user, no secrets in image)
- Reviewing Terraform configuration for correctness
- Grep-scanning all files for accidentally committed secrets