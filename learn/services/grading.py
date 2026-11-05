"""Deterministic grading without an LLM (PRD §9)."""

import re
import string
import unicodedata

LETTERS = string.ascii_uppercase

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")
# "B", "b)", "(b)", "B.", "option b", "answer: B"
_LETTER_ONLY_RE = re.compile(r"^(?:(?:option|answer|choice)\s*[:\-]?\s*)?\(?([a-z])\)?[\.\):]?$", re.IGNORECASE)
# "B) Paris", "b. Paris", "(b) Paris"
_LETTER_PREFIX_RE = re.compile(r"^\(?([a-z])[\)\.:]\s+(.+)$", re.IGNORECASE | re.DOTALL)


def normalise(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _compact(text: str) -> str:
    return normalise(text).replace(" ", "")


def option_letter(index: int) -> str:
    return LETTERS[index]


def resolve_mcq_correct_index(question) -> int | None:
    options = question.options_json or []
    correct = (question.correct_answer or "").strip()
    if len(correct) == 1 and correct.upper() in LETTERS[: len(options)]:
        return LETTERS.index(correct.upper())
    target = _compact(correct)
    for i, opt in enumerate(options):
        if _compact(opt) == target:
            return i
    return None


def _mcq_selected_index(question, answer: str) -> int | None:
    options = question.options_json or []
    raw = (answer or "").strip()
    if not raw:
        return None

    match = _LETTER_ONLY_RE.match(raw)
    if match:
        letter = match.group(1).upper()
        if letter in LETTERS[: len(options)]:
            return LETTERS.index(letter)

    # Exact option text (after normalisation).
    target = _compact(raw)
    for i, opt in enumerate(options):
        if _compact(opt) == target:
            return i

    match = _LETTER_PREFIX_RE.match(raw)
    if match:
        letter, rest = match.group(1).upper(), match.group(2)
        if letter in LETTERS[: len(options)]:
            idx = LETTERS.index(letter)
            # Accept "B) Paris" when the text matches the letter, or the text alone is ambiguous.
            if _compact(options[idx]) == _compact(rest):
                return idx
            for i, opt in enumerate(options):
                if _compact(opt) == _compact(rest):
                    return i
            return idx
    return None


def grade(question, answer: str) -> str:
    """Return one of Answer.CORRECT / INCORRECT / NEEDS_REVIEW."""
    from learn.models import Answer, Question

    if question.type == Question.MCQ:
        correct_idx = resolve_mcq_correct_index(question)
        selected = _mcq_selected_index(question, answer)
        if correct_idx is not None and selected == correct_idx:
            return Answer.CORRECT
        # Accepted alternative phrasings also count for MCQ.
        if _matches_accepted(question, answer):
            return Answer.CORRECT
        return Answer.INCORRECT

    if _matches_accepted(question, answer):
        return Answer.CORRECT
    return Answer.NEEDS_REVIEW


def _matches_accepted(question, answer: str) -> bool:
    candidate = _compact(answer)
    if not candidate:
        return False
    accepted = list(question.accepted_answers_json or [])
    if question.type == question.SHORT and question.correct_answer:
        accepted.append(question.correct_answer)
    return any(_compact(a) == candidate for a in accepted if a)


def display_correct_answer(question) -> str:
    if question.type == question.MCQ:
        idx = resolve_mcq_correct_index(question)
        if idx is not None:
            return f"{option_letter(idx)}) {question.options_json[idx]}"
    return question.correct_answer
