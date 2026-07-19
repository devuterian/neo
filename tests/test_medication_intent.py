import pytest

from neo.errors import ValidationError
from neo.medication_intent import (
    classify_medication_intent,
    medication_mutation_requires_confirmation,
    reply_timestamp_relation,
)


def test_medication_questions_are_read_only() -> None:
    for text in (
        "약 언제 먹었어?",
        "약 A 마지막으로 언제 했더라?",
        "오늘 약 B 먹은 기록 있어?",
        "무슨 약 기록 남아 있어?",
    ):
        assert classify_medication_intent(text) == "read_only_query"


def test_contradiction_requests_requery_without_mutation() -> None:
    assert classify_medication_intent("오늘 한 거 맞잖아") == "contradiction_requery"
    assert classify_medication_intent("그 기록 이상한데?") == "contradiction_requery"


def test_only_explicit_mutation_language_is_mutation() -> None:
    assert classify_medication_intent("기록해줘") == "explicit_add"
    assert classify_medication_intent("이 기록 지워줘") == "explicit_remove"
    assert classify_medication_intent("7시 3분으로 정정해줘") == "explicit_correct"


@pytest.mark.parametrize("candidate_count", [0, 2, 3])
def test_ambiguous_remove_or_correct_requires_confirmation(candidate_count: int) -> None:
    assert medication_mutation_requires_confirmation("explicit_remove", candidate_count)
    assert medication_mutation_requires_confirmation("explicit_correct", candidate_count)


def test_single_explicit_target_does_not_need_ambiguity_confirmation() -> None:
    assert not medication_mutation_requires_confirmation("explicit_remove", 1)
    assert not medication_mutation_requires_confirmation("explicit_correct", 1)
    assert not medication_mutation_requires_confirmation("explicit_add", 4)


def test_negative_candidate_count_is_invalid() -> None:
    with pytest.raises(ValidationError):
        medication_mutation_requires_confirmation("explicit_remove", -1)


def test_reply_timestamp_conflict_never_becomes_an_automatic_write() -> None:
    assert reply_timestamp_relation(
        "2026-07-12T07:03:00+09:00",
        "2026-07-12T07:04:00+09:00",
    ) == "conflict_requires_confirmation"
    assert reply_timestamp_relation(
        "2026-07-12T07:03:00+09:00",
        "2026-07-11T22:03:00Z",
    ) == "same_instant"
    assert reply_timestamp_relation(None, "2026-07-12T07:04:00+09:00") == "occurred_time_unknown"
