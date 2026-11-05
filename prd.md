# PRD — learnmcp (MVP)

> Version: 0.1 · Date: 2026-11-05 · Status: Draft for a Python MVP

## 1. Summary

learnmcp is an MCP server plus a web panel that connects an **instructor** to their **students' AI assistants**, even when students use the free versions of Claude or ChatGPT.

- The instructor creates classes, lessons and quizzes in the panel.
- The student joins with an invite link and adds learnmcp as a connector to their own AI.
- Inside the chat, the student reads lessons, takes quizzes and reports where they are stuck.
- The instructor sees scores, problem concepts and inactive students on a dashboard.

**Core insight:** there is always an instructor teaching something, and students already learn with AI, often on free plans. learnmcp makes that learning visible and measurable for the instructor, without asking students to learn a new tool.

## 2. MVP goals

Validate three assumptions within 4 to 6 weeks:

1. Students actually connect learnmcp to their AI (connection rate).
2. The AI calls the tools reliably and in-chat quizzes work.
3. Instructors find the dashboard valuable and are willing to pay for it.

**Success metrics:**

| Metric | Target |
|---|---|
| Connection rate (invited student → connector added) | ≥ 60% |
| Completion rate of started quizzes | ≥ 70% |
| Tool-call success (correct calls ÷ attempts) | ≥ 90% on Claude |
| Pilot instructors who open the dashboard at least weekly | ≥ 3 of 5 |
| Pilot instructors willing to pay after the pilot | ≥ 2 of 5 |

## 3. Users

### Instructor (future payer)
A private tutor, online course creator, workshop host or university lecturer. Wants to know what students know, where they get stuck and who is dropping out.

### Student (always free)
Uses Claude or ChatGPT, usually on a free plan. Does not want to install anything new. Must be able to see exactly what is shared with the instructor.

## 4. Platform constraints (November 2026)

| Platform | Free-plan student can connect? | MVP note |
|---|---|---|
| Claude | Yes, **one custom connector only** | Primary MVP platform; no approval needed |
| ChatGPT | Only via an app published in the App Directory (OpenAI review, outside the EU) | For testing: Developer mode on a Plus or Pro account (web only) |
| Gemini | Possibly via Spark (not confirmed in official docs) | Out of MVP scope; test later |
| DeepSeek | No (only via API in third-party clients) | Out of scope |

Sources: [Claude custom connectors](https://support.claude.com/en/articles/11175166) · [ChatGPT Developer mode](https://developers.openai.com/api/docs/guides/developer-mode) · [ChatGPT app submissions](https://openai.com/index/developers-can-now-submit-apps-to-chatgpt/)

**Design implications:**
- Test the MVP on **Claude** first, then on ChatGPT via Developer mode.
- Provide a **simple web quiz page** as a fallback for students who cannot connect (optional in the MVP, required in the next version).
- Tools must work reliably with free-tier models: few tools, clear names, simple inputs.

## 5. Key technical constraint

The MCP server **does not see the student's full conversation**. It only sees the arguments the model sends when it calls a tool.

- **Quizzes are reliable:** questions come from the server, answers go back to the server and grading happens on the server.
- **Logging every question is not reliable:** tracking is therefore based on **explicit events**: lesson started, quiz, "I'm stuck".
- **The correct answer is never** returned to the model before the student's answer has been submitted.

## 6. Scope

### In the MVP
1. **Instructor panel (Django admin):** sign up and log in; create a class, lessons (title, objectives, text content) and quizzes (multiple choice and short answer).
2. **Student onboarding:** invite link or code → name and email → consent page → personal MCP URL and connection instructions.
3. **MCP server** with the tools in section 8.
4. **Instructor dashboard:** quiz scores per student and per question, "stuck" concepts, students with no activity in the last 7 days.
5. **Student privacy page:** view recorded data; leave the class and delete the data.

### Out of the MVP
Payments, mobile app, Gemini and DeepSeek, LLM-based grading, automatic reminder emails, multiple instructors per class, PDF and video uploads, integrations with Teachable, Kajabi or LMSs, and full OAuth (the MVP uses a personal token; see section 10).

## 7. Proposed architecture

```
                 ┌────────────────────────────────────────┐
                 │  learnmcp (one Python project, ASGI)   │
 Student's AI    │                                        │
 (Claude/ChatGPT)│  /s/{token}/mcp ──► FastMCP app        │
   ── MCP ──────►│        │  (tools call Django ORM)      │
                 │        ▼                               │
                 │  Django ◄── /admin/  (instructor panel)│
 Instructor ────►│         ◄── /join/, /me/ (student)     │
   (browser)     │         ◄── /dashboard/ (custom view)  │
                 │  SQLite (dev) / Postgres (prod)        │
                 └────────────────────────────────────────┘
```

| Component | Proposed choice | Why |
|---|---|---|
| Language | Python 3.11+ | Founder's choice |
| Web framework and panel | **Django 5.x**; the instructor panel is **Django admin** with per-instructor permissions, plus one custom dashboard view | Admin gives CRUD for classes, lessons and quizzes almost for free |
| MCP server | Official Python SDK (`mcp`, `FastMCP` class) with **Streamable HTTP** transport | Remote connectors in Claude and ChatGPT need HTTP |
| Hosting both in one process | A small ASGI router (Starlette) that sends `/s/{token}/mcp` to the FastMCP app and everything else to Django's `get_asgi_application()` | One deploy, one database, one codebase |
| ORM access from MCP tools | Tools are `async` and call the ORM through `asgiref.sync.sync_to_async` (or Django's async ORM methods such as `aget`, `afilter`) | Django raises `SynchronousOnlyOperation` if the sync ORM runs in an async context |
| Database | SQLite in development, Postgres in production | Standard Django setup |
| Instructor auth | Django auth (`User` + `Instructor` profile), session login | Built in |
| Student auth for MCP | Random personal token in the URL path | Simplest option for a custom connector; see section 10 |
| ASGI server | Uvicorn | Required for Streamable HTTP |
| Local testing | MCP Inspector, pytest and pytest-django | Test tools without a real client |
| Public URL for testing | A tunnel (cloudflared or ngrok), then Render, Fly.io or Railway | Clients need a public HTTPS URL |

> Check exact SDK versions and APIs against the current `modelcontextprotocol/python-sdk` docs when implementing; the method that returns the Streamable HTTP ASGI app and its lifespan handling may change between versions. The FastMCP app's lifespan (session manager) must be started by the router.

**Sketch of the ASGI entry point:**

```python
# config/asgi.py
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount

from learn.mcp_server import mcp, TokenMiddleware  # FastMCP instance

django_app = get_asgi_application()
mcp_app = TokenMiddleware(mcp.streamable_http_app())  # resolves /s/{token}/ to a student

application = Starlette(
    routes=[
        Mount("/s", app=mcp_app),
        Mount("/", app=django_app),
    ],
    lifespan=lambda app: mcp.session_manager.run(),
)
```

## 8. MCP tools

Principles: few tools, clear verb names, descriptions that tell the model **when** to call each tool, and short structured outputs.

| Tool | Input | Output | When to call |
|---|---|---|---|
| `list_my_courses` | — | The student's classes and lessons, with the status of each lesson | When the student asks about their course, lessons or "what should I do" |
| `get_lesson` | `lesson_id` | Title, objectives, content and teaching instructions for the model | When the student wants to start or continue a lesson; records a `lesson_started` event |
| `start_quiz` | `quiz_id` | `attempt_id` and the **first question** (without the correct answer) | When the student asks for a quiz |
| `submit_answer` | `attempt_id`, `question_id`, `answer` | Correct or incorrect, a short explanation and the next question (or the end) | After each student answer; the model must not judge the answer itself |
| `report_stuck` | `lesson_id`, `concept`, `note` (optional) | Confirmation | When the student says they don't understand, or keeps getting one concept wrong |
| `get_progress` | — | Summary of the student's progress and a suggested next step | When the student asks "where am I" or "what's next" |

**Behaviour rules** (in tool descriptions and in the `get_lesson` output):
- Ask quiz questions one at a time and wait for the student's answer.
- Send the answer to `submit_answer` exactly as the student gave it; do not answer for them.
- If the student is stuck, call `report_stuck`, then explain.

**Sketch implementation:**

```python
# learn/mcp_server.py
from asgiref.sync import sync_to_async
from mcp.server.fastmcp import FastMCP

from learn.services import quizzes
from learn.context import current_enrollment   # set by TokenMiddleware

mcp = FastMCP("learnmcp")

@mcp.tool()
async def start_quiz(quiz_id: int) -> dict:
    """Start a quiz the instructor assigned. Call when the student asks for a quiz.
    Ask the returned question to the student and wait for their answer.
    Never answer it yourself."""
    return await sync_to_async(quizzes.start)(current_enrollment(), quiz_id)

@mcp.tool()
async def submit_answer(attempt_id: int, question_id: int, answer: str) -> dict:
    """Submit the student's answer exactly as they gave it. The server grades it."""
    return await sync_to_async(quizzes.grade_and_next)(
        current_enrollment(), attempt_id, question_id, answer
    )
```

Business logic lives in plain synchronous Django services (`learn/services/`), so it can be unit-tested with pytest-django and reused by both the MCP tools and the Django views.

## 9. Data model

Django models in one app (`learn`). Instructors use Django's built-in `User` for login.

| Model | Main fields |
|---|---|
| `Instructor` | user (OneToOne to `auth.User`), display_name, created_at |
| `Course` | id, instructor_id, title, description, join_code |
| `Lesson` | id, course_id, order, title, objectives, content, teaching_notes |
| `Quiz` | id, course_id, lesson_id (optional), title |
| `Question` | id, quiz_id, type (mcq or short), prompt, options_json, correct_answer, accepted_answers_json, explanation, concept |
| `Student` | id, name, email, created_at |
| `Enrollment` | id, student_id, course_id, token_hash, consent_at, joined_at, left_at |
| `QuizAttempt` | id, enrollment_id, quiz_id, started_at, finished_at, score |
| `Answer` | id, attempt_id, question_id, raw_answer, is_correct, answered_at |
| `Event` | id, enrollment_id, type (lesson_started, stuck, progress_viewed), lesson_id, concept, note, client (claude or chatgpt), created_at |

**Grading in the MVP (no LLM):**
- `mcq`: compare the option letter or text, case-insensitive.
- `short`: compare against `accepted_answers` after normalisation (strip spaces and punctuation, normalise characters). Otherwise mark as `needs_review` for the instructor.

## 10. Authentication and security

- **Instructors:** Django auth with session login. Each instructor is a staff user in an `Instructors` group with model permissions for `Course`, `Lesson`, `Quiz` and `Question`. Every `ModelAdmin` overrides `get_queryset` and `save_model` so instructors only see and edit their own classes. Superusers (the platform operator) see everything.
- **Students (MVP):** each enrollment gets a random 32-byte token; the student's personal URL is `https://host/s/{token}/mcp`. Only the token **hash** is stored. The student can revoke and regenerate the token.
- **Risk:** anyone with the URL can act as the student. Acceptable for a pilot, not for production.
- **Next version:** OAuth 2.1 following the MCP authorization spec; likely required for ChatGPT App Directory publication (verify at submission).
- Per-token rate limiting; log every tool call with `client` and timestamp.
- Never put email addresses or other personal data in query strings.

## 11. Privacy and consent

- Consent page before the MCP URL is created: what is recorded (events, quiz answers, "stuck" notes) and what is **not** recorded (the full conversation).
- On a "My data" page the student sees every recorded event and can leave the class; leaving deletes their data.
- No students under 18 in the MVP (age check at sign-up).
- Do not target EU customers at first (EU AI Act requirements for systems that evaluate learning outcomes).

## 12. Pages

**Instructor (Django admin at `/admin/`):**
1. Sign up page (simple Django view that creates a staff user in the `Instructors` group), then the standard admin login
2. `Course` admin: list and create classes; read-only join code and invite link with a copy button
3. `Course` change page with `Lesson` and `Quiz` as inlines
4. `Quiz` change page with `Question` as a tabular inline (type, prompt, options, accepted answers, concept)
5. Class dashboard: a custom admin view (registered through `ModelAdmin.get_urls`, linked from the `Course` page) with the student table (last activity, average score, number of "stuck" reports), most-missed questions and most frequent "stuck" concepts
6. `Enrollment` admin (read-only): per-student event and quiz history; `Answer` items with `needs_review` can be marked correct or incorrect

The admin is restyled only lightly in the MVP (site header, title, logo). A custom instructor frontend comes later if pilots show the admin is too technical.

**Student:**
1. `/join/{code}`: name, email, age confirmation and consent
2. Connect page: personal MCP URL, copy button and short instructions for adding a custom connector in Claude and Developer mode in ChatGPT
3. `/me`: my data, leave class, regenerate URL

## 13. Proposed project structure

```
learnmcp/
  manage.py
  config/
    settings.py
    urls.py            # /admin/, /join/, /me/, /signup/
    asgi.py            # Starlette router: /s/ → FastMCP, / → Django
  learn/               # single Django app
    models.py          # Instructor, Course, Lesson, Quiz, Question, Student,
                       # Enrollment, QuizAttempt, Answer, Event
    admin.py           # ModelAdmins with per-instructor filtering, inlines,
                       # custom dashboard view
    mcp_server.py      # FastMCP instance and async tool definitions
    context.py         # contextvar holding the current enrollment
    middleware.py      # TokenMiddleware: /s/{token}/mcp → enrollment
    services/
      quizzes.py       # start, grade, next question (sync, ORM)
      progress.py      # dashboard aggregates
      events.py
      tokens.py        # create, hash, revoke student tokens
    views.py           # signup, join, connect, my data
    templates/learn/
    management/commands/
      seed_demo.py     # demo instructor, course, quiz for testing
  tests/
    test_quizzes.py
    test_tools.py      # call tool functions with a fake enrollment
    test_admin_scoping.py  # instructors only see their own data
    test_tokens.py
  pyproject.toml
  README.md
```

Run locally with `uvicorn config.asgi:application --reload`; `python manage.py runserver` alone will not serve the MCP endpoint.

## 14. Test plan

1. **Unit (pytest + pytest-django):** grading (mcq and short with normalisation), question order, the correct answer never appearing in output before the student answers, token revocation, and admin scoping (an instructor cannot see or edit another instructor's classes).
2. **Tools locally:** run the server and exercise each tool with MCP Inspector.
3. **End to end with free Claude:** run the server behind an HTTPS tunnel, add the personal URL as a custom connector on a **free** Claude account, and run the scenarios below.
4. **End to end with ChatGPT:** the same scenarios via Developer mode on a Plus account on the web.
5. **Reliability:** run each scenario 10 times per client and record the share of correct tool calls.

**Acceptance scenarios:**

| # | Scenario | Expected result |
|---|---|---|
| 1 | Student: "What are my lessons?" | `list_my_courses` is called and the correct list is shown |
| 2 | Student: "Let's start lesson 2" | `get_lesson` is called and a `lesson_started` event appears on the dashboard |
| 3 | Student: "Quiz me" | Questions are asked one at a time and the score is recorded on the dashboard |
| 4 | Student gives a wrong answer | The model reports the result from `submit_answer`, not its own judgement |
| 5 | Student: "I don't get this" | `report_stuck` is recorded with the right concept |
| 6 | Revoked token | Tools return a clear "invalid connection" error |
| 7 | Student leaves the class | Their data disappears from the instructor dashboard |

## 15. Implementation milestones (proposed)

| Week | Deliverable |
|---|---|
| 1 | Django project and models, migrations, `seed_demo` command, ASGI router, MCP server with `list_my_courses` and `get_lesson`, tested with MCP Inspector |
| 2 | Quizzes (`start_quiz` and `submit_answer`), `report_stuck`, unit tests; first real connection to free Claude through a tunnel |
| 3 | Django admin for instructors (per-instructor scoping, inlines, signup) and student onboarding with consent |
| 4 | Instructor dashboard, "My data" page, ChatGPT testing via Developer mode, deployment |
| 5–6 | Pilot with 3 to 5 real instructors and measure the metrics in section 2 |

## 16. Open questions

1. Do free-tier Claude models call the tools reliably in long conversations? (Measure with the section 14 tests.)
2. How much does the one-custom-connector limit on free Claude block connection?
3. What exactly does ChatGPT App Directory publication require (OAuth, privacy policy, country settings)?
4. Does Gemini (via Spark) actually accept custom connectors on a free account?
5. Do instructors prefer to write quizzes themselves or have them generated from lesson content? (Generation in a later version.)

## 17. Risks

| Risk | MVP mitigation |
|---|---|
| Connector policy changes in Claude or ChatGPT | Support both; web quiz page as a fallback |
| Free-tier models calling tools inconsistently | Few simple tools, precise descriptions, measured in testing |
| Leaked personal student URL | Token hashing, revocation, OAuth in the next version |
| Students feeling "tracked" | Explicit consent, no full-conversation logging, "My data" page |
| Instructors not paying | Test willingness to pay in weeks 5–6 before building payments |
