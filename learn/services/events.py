from learn.models import Event


def record(
    enrollment,
    type_: str,
    *,
    lesson=None,
    attempt=None,
    concept: str = "",
    note: str = "",
    category: str = "",
    severity: str = "",
    client: str = "",
) -> Event:
    event = Event.objects.create(
        enrollment=enrollment,
        type=type_,
        lesson=lesson,
        attempt=attempt,
        concept=(concept or "").strip()[:200],
        note=(note or "").strip()[:2000],
        category=category or "",
        severity=severity or "",
        client=client or "",
    )
    enrollment.touch()
    return event
