from __future__ import annotations

from datetime import datetime

from .group_qa_models import GroupQuestionClassification
from .group_qa_settings import DEFAULT_TOPICS


SENSITIVE_TERMS = (
    "spark",
    "private spark",
    "프라이빗 스파크",
    "병원",
    "약",
    "병원",
    "medical",
    "정신과",
    "상담",
    "우울",
    "불안",
    "자살",
    "성별",
    "트랜스",
    "수술",
    "주소",
    "어디 살아",
    "위치",
    "어디야",
    "집",
    "이동",
    "동선",
    "돈",
    "수입",
    "세금",
    "계좌",
    "계약",
    "견적",
    "대금",
    "남친",
    "가족",
    "연애",
    "싸웠",
    "관계",
    "클라이언트",
    "납품",
    "파일",
    "로그",
    "대화",
    "dm",
    "메시지",
    "정치",
    "종교",
    "투표",
    "정당",
    "회의",
    "일정",
    "캘린더",
    "참석자",
    "장소",
    "왜",
    "무슨 일",
    "자세히",
    "정확히",
    "누구랑",
)
SPARK_TERMS = ("spark", "private spark", "프라이빗 스파크")
GROUP_MODEL_HARD_DENY_TERMS = SPARK_TERMS + (
    "data/private/spark",
    "credential",
    "token",
    "api key",
    ".env",
    "dm 원문",
    "message-log",
    "계좌",
    "세금",
    "정확한 집 주소",
)
MEDICAL_TERMS = ("medical", "병원", "진료", "검진")


def _normalized(value: str) -> str:
    return " ".join((value or "").casefold().split())


def is_group_private_spark_question(text: str) -> bool:
    """Hard pre-router deny for private-spark questions."""

    normalized = _normalized(text)
    return any(token in normalized for token in SPARK_TERMS) or "data/private/spark" in normalized


def is_group_model_hard_deny(text: str) -> bool:
    """Block non-projectable secrets and private-source requests before model routing."""

    normalized = _normalized(text)
    return any(token in normalized for token in GROUP_MODEL_HARD_DENY_TERMS)


def bucket_time(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    try:
        point = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if 5 <= point.hour < 12:
        return "morning"
    if 12 <= point.hour < 18:
        return "afternoon"
    if 18 <= point.hour < 22:
        return "evening"
    if point.hour >= 22:
        return "night"
    return "late_night"


def redact_public_text(value: str, *, allow_project_terms: bool = False) -> str | None:
    """Return a short public-safe string, or None when it must be withheld."""

    text = " ".join(str(value).split()).strip()
    if not text or any(word.casefold() in text.casefold() for word in SENSITIVE_TERMS):
        return None
    if not allow_project_terms:
        return None
    return text[:80]


def classify_group_question(
    text: str,
    allowed_topics: set[str] | None = None,
) -> GroupQuestionClassification:
    normalized = _normalized(text)
    if any(token in normalized for token in SPARK_TERMS):
        return GroupQuestionClassification(
            "spark_sensitive", False, "private spark is never available in groups"
        )
    if any(token in normalized for token in MEDICAL_TERMS):
        topics = allowed_topics or DEFAULT_TOPICS
        return GroupQuestionClassification("medical", "medical" in topics, "trusted-only medical topic")
    if any(token.casefold() in normalized for token in SENSITIVE_TERMS):
        return GroupQuestionClassification("sensitive", False, "sensitive topic")

    topics = allowed_topics if allowed_topics is not None else DEFAULT_TOPICS
    patterns = (
        ("wake", ("일어났", "기상", "깼")),
        ("sleep", ("잤", "잠", "취침", "자러", "수면", "자냐", "자니")),
        ("meal", ("밥", "먹었", "식사", "메뉴", "뭐 먹")),
        ("outing", ("외출", "나갔", "밖", "어디 갔", "돌아왔")),
        ("work_now", ("작업 중", "일하는 중", "바빠", "지금 작업")),
        ("work_time", ("언제 작업", "작업했", "체크인", "체크아웃")),
        ("completed_today", ("끝냈", "끝낸", "완료", "한 일", "처리한 것")),
        ("todo_today", ("할 일", "남은 일", "오늘 뭐 해")),
        ("availability", ("연락해도", "깨워도", "멘션해도", "지금 가능")),
        ("light_status", ("컨디션", "상태")),
    )
    for category, words in patterns:
        if any(word in normalized for word in words):
            return GroupQuestionClassification(
                category,
                category in topics,
                "topic allowlist" if category in topics else "topic disabled",
            )
    return GroupQuestionClassification("unsupported", False, "unsupported public question")
