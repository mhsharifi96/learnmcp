"""Exercise the MCP tools: in-process through the SDK client, and over HTTP through the
real ASGI router (/s/{token}/mcp) to cover token resolution and lifespan wiring."""

import json

import httpx2
import pytest
from asgiref.sync import sync_to_async
from mcp import Client

from learn.context import current_client, current_token
from learn.mcp_server import mcp
from learn.models import Event, ToolCall
from learn.services import enrollments, tokens

pytestmark = pytest.mark.django_db(transaction=True)


def payload(result):
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


def error_text(result):
    return " ".join(getattr(c, "text", "") for c in result.content)


@pytest.fixture
def as_student(enrolled):
    enrollment, raw = enrolled
    t1, t2 = current_token.set(raw), current_client.set("claude")
    yield enrollment
    current_token.reset(t1)
    current_client.reset(t2)


async def test_tool_list_is_small_and_described():
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == {
        "list_my_courses", "get_lesson", "start_quiz", "submit_answer", "report_stuck", "get_progress",
    }
    for tool in tools:
        assert "Call" in (tool.description or "")


async def test_full_student_session(as_student, course_setup):
    enrollment = as_student
    course, lesson1, lesson2, quiz = course_setup
    async with Client(mcp) as client:
        courses = payload(await client.call_tool("list_my_courses", {}))
        lessons = courses["courses"][0]["lessons"]
        assert [l["title"] for l in lessons] == ["Variables", "Loops"]
        assert lessons[0]["status"] == "not_started"

        lesson = payload(await client.call_tool("get_lesson", {"lesson_id": lesson1.id}))
        assert lesson["title"] == "Variables" and "how_to_teach" in lesson

        started = payload(await client.call_tool("start_quiz", {"quiz_id": quiz.id}))
        assert "correct_answer" not in json.dumps(started)
        r1 = payload(
            await client.call_tool(
                "submit_answer",
                {"attempt_id": started["attempt_id"], "question_id": started["question"]["question_id"], "answer": "b"},
            )
        )
        assert r1["result"] == "correct"
        r2 = payload(
            await client.call_tool(
                "submit_answer",
                {"attempt_id": started["attempt_id"], "question_id": r1["next_question"]["question_id"], "answer": "type()"},
            )
        )
        assert r2["finished"] and r2["score"]["score_percent"] == 100

        stuck = payload(
            await client.call_tool("report_stuck", {"lesson_id": lesson2.id, "concept": "for loops", "note": "range?"})
        )
        assert stuck["recorded"]

        progress = payload(await client.call_tool("get_progress", {}))
        assert progress["courses"][0]["average_quiz_score_percent"] == 100
        assert "Loops" in progress["courses"][0]["suggested_next_step"]

    types = await sync_to_async(lambda: set(Event.objects.filter(enrollment=enrollment).values_list("type", flat=True)))()
    assert {"lesson_started", "quiz_started", "quiz_finished", "stuck", "progress_viewed"} <= types
    stuck_event = await sync_to_async(Event.objects.get)(enrollment=enrollment, type="stuck")
    assert stuck_event.concept == "for loops" and stuck_event.lesson_id == lesson2.id and stuck_event.client == "claude"
    calls = await sync_to_async(lambda: list(ToolCall.objects.values_list("tool", "ok")))()
    assert len(calls) == 7 and all(ok for _, ok in calls)


async def test_bad_ids_return_readable_errors(as_student):
    async with Client(mcp) as client:
        result = await client.call_tool("get_lesson", {"lesson_id": 99999})
    assert result.is_error and "list_my_courses" in error_text(result)


async def test_revoked_token_gives_invalid_connection(enrolled):
    enrollment, raw = enrolled
    await sync_to_async(tokens.assign_new_token)(enrollment)
    reset = current_token.set(raw)
    try:
        async with Client(mcp) as client:
            result = await client.call_tool("list_my_courses", {})
    finally:
        current_token.reset(reset)
    assert result.is_error and "Invalid connection" in error_text(result)
    assert await sync_to_async(ToolCall.objects.filter(ok=False, error="invalid_connection").count)() == 1


async def test_one_connector_covers_all_classes_of_same_student(as_student, other_instructor):
    from tests.conftest import make_course

    enrollment = as_student
    other_course = (await sync_to_async(make_course)(other_instructor, "Second class"))[0]
    await sync_to_async(enrollments.join)(
        other_course, name="Sam", email="sam@example.com", existing_student=enrollment.student
    )
    async with Client(mcp) as client:
        courses = payload(await client.call_tool("list_my_courses", {}))
    assert {c["title"] for c in courses["courses"]} == {"Python 101", "Second class"}


# --------------------------------------------------------------------------- over HTTP


MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}




async def _rpc(client, url, method, params, rid=1, headers=None):
    body = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
    return await client.post(url, json=body, headers={**MCP_HEADERS, **(headers or {})})


async def test_http_router_resolves_token(enrolled):
    # The MCP session manager can run once per process, so only this test starts the lifespan.
    from config.asgi import application, mcp_app

    _, raw = enrolled
    transport = httpx2.ASGITransport(app=application)
    async with (
        mcp_app.router.lifespan_context(mcp_app),
        httpx2.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        url = f"/s/{raw}/mcp"
        init = await _rpc(
            client, url, "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}},
            headers={"user-agent": "Claude-User"},
        )
        assert init.status_code == 200, init.text
        version = init.json()["result"]["protocolVersion"]
        extra = {"mcp-protocol-version": version, "user-agent": "Claude-User"}
        res = await _rpc(client, url, "tools/call", {"name": "list_my_courses", "arguments": {}}, rid=2, headers=extra)
        assert res.status_code == 200, res.text
        result = res.json()["result"]
        assert not result.get("isError"), result
        assert "Python 101" in json.dumps(result)

        # Unknown-format token is rejected before reaching MCP; Django still serves other paths.
        assert (await client.post("/s/bad!token/mcp", json={})).status_code == 404
        assert (await client.get("/healthz")).status_code == 200

    call = await sync_to_async(ToolCall.objects.get)(tool="list_my_courses")
    assert call.client == "claude"


async def test_rate_limit_per_token():
    from learn.middleware import RateLimiter, TokenMiddleware

    seen = []

    async def inner_app(scope, receive, send):
        seen.append(scope["state"]["learnmcp_token"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    app = TokenMiddleware(inner_app, RateLimiter(2))

    async def router(scope, receive, send):
        await app(scope, receive, send, token=scope["path"].split("/")[2])

    tok_a, tok_b = tokens.generate_token(), tokens.generate_token()
    transport = httpx2.ASGITransport(app=router)
    async with httpx2.AsyncClient(transport=transport, base_url="http://testserver") as client:
        codes_a = [(await client.post(f"/s/{tok_a}/mcp")).status_code for _ in range(3)]
        code_b = (await client.post(f"/s/{tok_b}/mcp")).status_code
    assert codes_a == [200, 200, 429]
    assert code_b == 200
    assert seen == [tok_a, tok_a, tok_b]
