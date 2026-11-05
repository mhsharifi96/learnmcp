from learn.models import Enrollment
from learn.services import enrollments, tokens


def test_only_hash_is_stored(enrolled):
    enrollment, raw = enrolled
    enrollment.refresh_from_db()
    assert enrollment.token_hash == tokens.hash_token(raw)
    assert raw not in enrollment.token_hash
    assert enrollment.token_hint == raw[-4:]
    assert len(raw) >= 40


def test_resolve_and_revoke(enrolled):
    enrollment, raw = enrolled
    assert tokens.resolve(raw) == enrollment
    new_raw = tokens.assign_new_token(enrollment)
    assert tokens.resolve(raw) is None
    assert tokens.resolve(new_raw) == enrollment
    assert tokens.resolve("not a token!") is None
    assert tokens.resolve("") is None


def test_extract_token_from_url():
    raw = tokens.generate_token()
    assert tokens.extract_token_from_url(f"https://host/s/{raw}/mcp") == raw
    assert tokens.extract_token_from_url(raw) == raw
    assert tokens.extract_token_from_url("https://host/admin/") is None


def test_leave_deletes_everything(enrolled):
    enrollment, raw = enrolled
    student = enrollment.student
    enrollments.leave(enrollment)
    assert not Enrollment.objects.filter(pk=enrollment.pk).exists()
    assert not type(student).objects.filter(pk=student.pk).exists()
    assert tokens.resolve(raw) is None
