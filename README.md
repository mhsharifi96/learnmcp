# learnmcp

An MCP server and a Django panel that connect an **instructor** to their **students' AI assistants** (Claude, ChatGPT), including free plans. See [prd.md](prd.md) for the product spec.

- Instructors create classes, lessons and quizzes in Django admin (`/admin/`) and watch a per-class dashboard.
- Students join with a code or link, give consent and get a **personal MCP URL** (`/s/{token}/mcp`) to add as a custom connector.
- In chat, the AI uses seven tools: `list_my_courses`, `get_lesson`, `start_quiz`, `submit_answer`, `record_ai_answer`, `report_stuck` and `get_progress`.
- Lessons: the instructor writes either the full lesson text or just a short **lesson prompt**; with only a prompt, the student's AI builds the lesson plan itself.
- Quizzes have two modes. **I write the questions**: graded on the server, and the correct answer is never sent before the student answers. **The AI writes the questions from my prompt**: the student's AI writes and judges each question and records it with `record_ai_answer`, so the instructor still sees every question, answer and score.
- Web UI: a bilingual (Persian/English) Next.js app in [frontend/](frontend/) for students (join, connect, my data) and instructors (classes, lessons, quizzes, dashboard, review). It talks to Django through the JSON API under `/api/`. In Docker, an nginx `gateway` service sends `/api`, `/admin`, `/s/` (MCP), OAuth and `/static` to Django and everything else to Next.js. Django admin stays available at `/admin/`.

## Architecture

```
uvicorn config.asgi:application
  └─ LearnMCPRouter (learn/middleware.py)
       ├─ /s/{token}/mcp → TokenMiddleware (rate limit, token → request state) → MCP Streamable HTTP app
       ├─ lifespan       → MCP session manager
       └─ everything else → Django (admin, /join/, /connect/, /me/, /signup/, /healthz)
```

| Path | What |
|---|---|
| `learn/services/` | All business logic: plain synchronous Django code, shared by the MCP tools and the views |
| `learn/mcp_server.py` | `MCPServer` instance and its six async tools. They call services via `sync_to_async`, map errors to readable tool errors and log every call to `ToolCall` |
| `learn/admin.py` | Instructor panel. Every `ModelAdmin` is scoped to the logged-in instructor; includes the dashboard view |
| `learn/views.py` | Instructor signup and the student join, consent, connect, "My data", regenerate and leave pages |

**SDK note:** the PRD mentions `FastMCP`. The current official SDK (`mcp` 2.x) renamed it to `MCPServer` (`mcp.server.mcpserver`), and this project uses that. The server runs **stateless with JSON responses**, so restarts, multiple workers and multiple replicas don't break students' connectors.

### Decisions beyond the PRD

- **One connector covers all classes.** Free Claude allows only one custom connector, so a student's token gives access to every class *that same student* joined. Students are linked across classes only through the same browser session at join time (or "restore with my URL"), never by matching an unverified email.
- **Unfinished quizzes resume** when `start_quiz` is called again, instead of starting over.
- **Revoked or unknown tokens** still reach the MCP layer, and every tool returns a clear "Invalid connection" message (PRD acceptance scenario 6). Malformed tokens get a 404.
- **Short answers** that don't match an accepted answer are marked `needs_review`. Instructors resolve them in *Answers* with the "Mark correct" or "Mark incorrect" actions, and scores are recalculated.
- **`ToolCall` audit log** (operator-only) records every tool call with client, success and duration. The dashboard shows the tool-call success rate (PRD metric 3).

## Local development

Requires [uv](https://docs.astral.sh/uv/) (Python 3.12 is fetched automatically).

```bash
uv sync
DJANGO_DEBUG=true uv run python manage.py migrate
DJANGO_DEBUG=true uv run python manage.py seed_demo          # prints instructor login + a student MCP URL
DJANGO_DEBUG=true uv run uvicorn config.asgi:application --reload
```

`manage.py runserver` does **not** serve the MCP endpoint; always use uvicorn.

- Instructor panel: http://localhost:8000/admin/ (demo user `demo` / `demo-pass-123`; sign up at `/signup/`)
- Student invite: http://localhost:8000/join/DEMOPY/
- Inspect the tools: `npx @modelcontextprotocol/inspector`, transport "Streamable HTTP", URL = the printed MCP URL

### Tests

```bash
uv run pytest          # or ./deploy.sh test
```

The tests cover grading (MCQ letter/text, short-answer normalisation), question order, the correct answer never leaking before the student answers, quiz resume and double-answer handling, token hashing and revocation, cross-student isolation, admin scoping (lists, change pages, delete, FK choices, dashboard), the review action, join/consent/leave/regenerate flows, and the MCP tools in-process and over HTTP through the real router.

## Testing with a real Claude or ChatGPT

Clients need a public HTTPS URL. For a quick test:

```bash
cloudflared tunnel --url http://localhost:8000      # prints https://xyz.trycloudflare.com
```

Set `PUBLIC_BASE_URL=https://xyz.trycloudflare.com`, add the host to `DJANGO_ALLOWED_HOSTS` and the URL to `DJANGO_CSRF_TRUSTED_ORIGINS`, then restart. Join the demo class (or run `seed_demo --base-url https://xyz.trycloudflare.com`) and add the personal URL:

- **Claude:** Settings → Connectors → *Add custom connector* → paste the URL.
- **ChatGPT:** enable Developer mode (Plus/Pro, web) → create an app with the URL and no authentication.

Then run the acceptance scenarios in PRD §14.

## Deployment (Docker)

`docker-compose.yml` runs **Postgres 17**, the **web** app (uvicorn, migrations on start) and an optional **Caddy** reverse proxy with automatic Let's Encrypt HTTPS (compose profile `https`).

On a server with Docker and the Compose plugin, with DNS for your domain pointing at it and ports 80 and 443 open:

```bash
git clone <repo> learnmcp && cd learnmcp
./deploy.sh init --domain learn.example.com   # writes .env with random secrets
./deploy.sh deploy                            # build, start, wait for health
./deploy.sh createsuperuser                   # platform operator account
```

To run locally in Docker without HTTPS: `./deploy.sh init --local && ./deploy.sh deploy` → http://localhost:8000.

| Command | What it does |
|---|---|
| `./deploy.sh deploy [--pull] [--no-backup]` | Optional `git pull`, Postgres backup, image build, `up -d`, wait for the health check, show URLs |
| `./deploy.sh rollback` | Restart the previous image (migrations are not reverted) |
| `./deploy.sh backup` / `restore FILE` | `pg_dump` to `backups/` (keeps 14) / restore with confirmation |
| `./deploy.sh status`, `logs [svc]`, `up`, `down`, `restart` | Day-to-day operations |
| `./deploy.sh migrate`, `seed`, `manage <args>` | Django management commands in the container |

To run behind your own proxy or a PaaS (Render, Fly.io, Railway), leave `COMPOSE_PROFILES` empty, or build the `Dockerfile` directly and set `DATABASE_URL`. The proxy must not buffer responses for `/s/*`.

### Configuration

All settings are environment variables; see [.env.example](.env.example). The key ones are `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `PUBLIC_BASE_URL`, `DATABASE_URL` (set by compose), `WEB_CONCURRENCY`, `MCP_RATE_LIMIT_PER_MINUTE` and `MCP_ALLOWED_HOSTS` (optional DNS-rebinding protection).

## Known MVP limitations

- Auth is a personal URL token (PRD §10). Anyone with the URL can act as the student; students can regenerate it on "My data". OAuth 2.1 is planned for the next version.
- The rate limiter is in-memory, per worker process.
- The "My data" page is reached through the browser session that joined, or by pasting the personal URL on `/me/restore/`.
- The connector setup steps on the connect page reflect the Claude and ChatGPT UIs as of November 2026; check them during the pilot.
