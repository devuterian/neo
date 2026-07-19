"""Safe, read-only public projection for Telegram group Q&A.

This module is the stable compatibility facade. Settings, policy, canonical JSON
projection, and rendering live in focused modules so privacy boundaries can be
reviewed independently.
"""
from __future__ import annotations

from .group_qa_brief_projection import (
    build_trusted_group_brief_context,
    build_trusted_group_brief_summary,
)
from .group_qa_models import (
    GroupPublicStatus,
    GroupQAResponse,
    GroupQASettings,
    GroupQuestionClassification,
    TrustedGroupBriefSummary,
)
from .group_qa_policy import (
    bucket_time,
    classify_group_question,
    is_group_model_hard_deny,
    is_group_private_spark_question,
    redact_public_text,
)
from .group_qa_projection import (
    build_group_public_status,
    build_trusted_group_model_context,
)
from .group_qa_renderer import (
    answer_group_brief,
    answer_group_question,
    build_group_brief_response,
)
from .group_qa_settings import normalize_chat_id, parse_group_qa_settings


__all__ = [
    "GroupPublicStatus",
    "GroupQAResponse",
    "GroupQASettings",
    "GroupQuestionClassification",
    "TrustedGroupBriefSummary",
    "answer_group_brief",
    "answer_group_question",
    "bucket_time",
    "build_group_brief_response",
    "build_group_public_status",
    "build_trusted_group_brief_context",
    "build_trusted_group_brief_summary",
    "build_trusted_group_model_context",
    "classify_group_question",
    "is_group_model_hard_deny",
    "is_group_private_spark_question",
    "normalize_chat_id",
    "parse_group_qa_settings",
    "redact_public_text",
]
