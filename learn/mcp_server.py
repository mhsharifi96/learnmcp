"""learnmcp MCP server: eight tools that call the synchronous Django services."""

import logging
import time
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations

from learn.context import STATE_CLIENT_KEY, STATE_TOKEN_KEY, current_client, current_token
from learn.models import ToolCall
from learn.services import ServiceError, courses, enrollments, progress, quizzes, tokens

logger = logging.getLogger("learnmcp.tools")

INVALID_CONNECTION = (
    "Invalid connection: this learnmcp link is unknown or was revoked. "
    "Tell the student to open their learnmcp 'My data' page, copy their current personal URL "
    "and update the connector."
)

INSTRUCTIONS = """learnmcp connects this student to the course their instructor teaches.
- Use list_my_courses when the student asks about their course, lessons, or what to do.
- Use get_lesson to teach a lesson; follow its how_to_teach rules.
- Some lessons contain only the instructor's short prompt: then build the lesson plan yourself from it.
- Quizzes: call start_quiz and follow its instructions. Instructor-written quizzes are graded by the server:
  ask ONE question at a time, wait for the reply and pass it unchanged to submit_answer; never grade it yourself.
  AI-generated quizzes (mode "ai_generated"): write one question at a time from the instructor's prompt,
  wait for the reply, judge it, and record it with record_ai_answer. Never answer for the student.
- When a quiz finishes, report each mistake to the student, then call submit_quiz_report with a short summary.
- Whenever the student has a learning problem (doesn't understand, keeps making the same mistake, lacks
  background, loses focus, or has a technical issue), call report_problem so the instructor can follow up.
- Use get_progress when the student asks where they are or what's next.
Only explicit tool calls are shared with the instructor; the conversation itself is not recorded."""

mcp = MCPServer(
    "learnmcp",
    title="learnmcp",
    instructions=INSTRUCTIONS,
    version="0.1.0",
    log_level=settings.LOGGING.get("root", {}).get("level", "INFO"),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)


def _identity(ctx: Context | None) -> tuple[str | None, str]:
    token, client = current_token.get(), current_client.get()
    if ctx is not None:
        try:
            request = ctx.request_context.request
        except ValueError:
            request = None
        scope = getattr(request, "scope", None) or {}
        state = scope.get("state") or {}
        token = state.get(STATE_TOKEN_KEY, token)
        client = state.get(STATE_CLIENT_KEY, client)
    return token, client or ""


def _run_sync(tool: str, token: str | None, client: str, fn, kwargs: dict):
    close_old_connections()
    started = time.monotonic()
    enrollment = tokens.resolve(token) if token else None
    ok, error = True, ""
    try:
        if enrollment is None:
            ok, error = False, "invalid_connection"
            raise ToolError(INVALID_CONNECTION)
        try:
            return fn(enrollment, client=client, **kwargs)
        except ServiceError as exc:
            ok, error = False, str(exc)
            raise ToolError(str(exc)) from exc
        except Exception:
            ok, error = False, "internal_error"
            logger.exception("Tool %s failed", tool)
            raise ToolError("Something went wrong on the learnmcp server. Please try again in a moment.") from None
    finally:
        try:
            ToolCall.objects.create(
                enrollment=enrollment,
                tool=tool,
                client=client[:30],
                ok=ok,
                error=error[:300],
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception:  # never let audit logging break a tool call
            logger.exception("Could not log tool call")
        logger.info("tool=%s client=%s ok=%s", tool, client or "-", ok)
        close_old_connections()


async def _call(ctx: Context | None, tool: str, fn, **kwargs):
    token, client = _identity(ctx)
    return await sync_to_async(_run_sync)(tool, token, client, fn, kwargs)


# --------------------------------------------------------------------------- tools


@mcp.tool(title="List my courses", annotations=READ_ONLY, structured_output=True)
async def list_my_courses(ctx: Context) -> dict[str, Any]:
    """List the student's classes with their lessons (lesson_id, status) and quizzes (quiz_id).

    Call this when the student asks about their course or lessons, asks "what should I do?",
    or whenever you need a lesson_id or quiz_id."""
    return await _call(ctx, "list_my_courses", lambda e, client: courses.list_courses(e))


@mcp.tool(title="Get lesson", annotations=READ_ONLY, structured_output=True)
async def get_lesson(lesson_id: int, ctx: Context) -> dict[str, Any]:
    """Get a lesson's title, objectives, content and teaching instructions.

    Call this when the student wants to start or continue a lesson. Teach from the returned
    content and follow its how_to_teach rules. Get lesson ids from list_my_courses."""
    return await _call(ctx, "get_lesson", courses.get_lesson, lesson_id=lesson_id)


@mcp.tool(title="Start quiz", annotations=WRITE, structured_output=True)
async def start_quiz(quiz_id: int, ctx: Context) -> dict[str, Any]:
    """Start (or resume) a quiz the instructor assigned. Returns attempt_id and instructions.

    Call this when the student asks to be quizzed or tested. For instructor-written quizzes it returns
    the first question: ask it exactly, then STOP and wait for the student's answer. For AI-generated
    quizzes (mode "ai_generated") it returns the instructor's prompt: write the questions yourself,
    one at a time, and record each answer with record_ai_answer. Never answer for the student."""
    return await _call(ctx, "start_quiz", quizzes.start, quiz_id=quiz_id)


@mcp.tool(title="Submit answer", annotations=WRITE, structured_output=True)
async def submit_answer(attempt_id: int, question_id: int, answer: str, ctx: Context) -> dict[str, Any]:
    """Submit the student's answer to the current quiz question. The server grades it.

    Call this after EVERY student answer during a quiz. Pass the answer exactly as the student
    gave it (a letter like "B" or the option text is fine). Do not judge the answer yourself:
    tell the student the returned result and explanation, then ask the next_question."""
    return await _call(
        ctx, "submit_answer", quizzes.grade_and_next, attempt_id=attempt_id, question_id=question_id, answer=answer
    )


@mcp.tool(title="Record AI quiz answer", annotations=WRITE, structured_output=True)
async def record_ai_answer(
    attempt_id: int,
    question: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    ctx: Context,
    options: list[str] | None = None,
    explanation: str = "",
    concept: str = "",
) -> dict[str, Any]:
    """Record one question of an AI-generated quiz (start_quiz returned mode "ai_generated").

    Call this after EVERY student answer in such a quiz. question: the exact question you asked.
    options: the answer options for multiple choice, in order (omit for short answers).
    correct_answer: the right answer. student_answer: the student's reply, unchanged.
    is_correct: your fair judgement of the reply. explanation: one line shown to the instructor.
    concept: a few words naming what the question tests. Then follow the returned instructions."""
    return await _call(
        ctx,
        "record_ai_answer",
        quizzes.record_ai_answer,
        attempt_id=attempt_id,
        question=question,
        correct_answer=correct_answer,
        student_answer=student_answer,
        is_correct=is_correct,
        options=options,
        explanation=explanation,
        concept=concept,
    )


@mcp.tool(title="Report a student problem", annotations=WRITE, structured_output=True)
async def report_problem(
    concept: str,
    ctx: Context,
    category: str = "concept",
    severity: str = "medium",
    lesson_id: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Tell the instructor about a learning problem so they can follow up with the student.

    Call this when the student says they don't understand something, keeps making the same mistake,
    is missing background knowledge, loses motivation, or hits a technical issue.
    concept: a few words naming the topic (e.g. "past simple irregular verbs").
    category: one of concept, repeated_mistake, prerequisite, engagement, technical, other.
    severity: low, medium or high (high = the student cannot continue without help).
    lesson_id: the current lesson, if known. note: one or two sentences describing what went wrong.
    Call it first, then help the student a different way."""
    return await _call(
        ctx,
        "report_problem",
        enrollments.report_problem,
        lesson_id=lesson_id,
        concept=concept,
        category=category,
        severity=severity,
        note=note,
    )


@mcp.tool(title="Submit quiz report", annotations=WRITE, structured_output=True)
async def submit_quiz_report(
    attempt_id: int, summary: str, ctx: Context, weak_concepts: list[str] | None = None
) -> dict[str, Any]:
    """Send the instructor a short report after a quiz is finished.

    Call this once, right after the last answer of a quiz (when the response has finished=true).
    summary: 2-4 sentences on how the quiz went, which questions the student got wrong and what
    they seem to misunderstand. weak_concepts: the concepts the student should review."""
    return await _call(
        ctx, "submit_quiz_report", quizzes.submit_report, attempt_id=attempt_id, summary=summary,
        weak_concepts=weak_concepts,
    )


@mcp.tool(title="Get progress", annotations=READ_ONLY, structured_output=True)
async def get_progress(ctx: Context) -> dict[str, Any]:
    """Summarise the student's progress (lessons, quiz scores, open problems) and suggest a next step.

    Call this when the student asks "where am I?", "how am I doing?" or "what's next?"."""
    return await _call(ctx, "get_progress", progress.student_progress)


# --------------------------------------------------------------------------- ASGI app


def build_http_app():
    """Build the Streamable HTTP ASGI app (served at /mcp; the router maps /s/{token}/mcp)."""
    if settings.MCP_ALLOWED_HOSTS:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.MCP_ALLOWED_HOSTS,
            allowed_origins=[f"https://{h.split(':')[0]}" for h in settings.MCP_ALLOWED_HOSTS]
            + ["https://claude.ai", "https://chatgpt.com"],
        )
    else:
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    # Stateless + JSON responses: every request is independent, so the process can be
    # restarted or scaled horizontally without breaking students' connectors.
    return mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
