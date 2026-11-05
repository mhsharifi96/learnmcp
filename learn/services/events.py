from learn.models import Event


def record(enrollment, type_: str, *, lesson=None, concept: str = "", note: str = "", client: str = "") -> Event:
    event = Event.objects.create(
        enrollment=enrollment,
        type=type_,
        lesson=lesson,
        concept=(concept or "").strip()[:200],
        note=(note or "").strip()[:2000],
        client=client or "",
    )
    enrollment.touch()
    return event
