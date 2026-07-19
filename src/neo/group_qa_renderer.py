from __future__ import annotations

from typing import Any, Literal

from .group_qa_models import (
    GroupPublicStatus,
    GroupQAResponse,
    GroupQuestionClassification,
)


def answer_group_question(
    classification: GroupQuestionClassification,
    context: GroupPublicStatus,
    *,
    max_chars: int = 300,
) -> str:
    if classification.category in {"spark_sensitive", "sensitive"}:
        answer = "그건 단체방에서는 말할 수 없어."
    elif not classification.allowed:
        answer = "그건 여기서 확인할 수 없어."
    elif classification.category == "medical":
        if not context.trusted:
            answer = "병원 기록은 trusted 단체방에서만 확인할 수 있어."
        elif not context.medical_available:
            answer = "주기가 설정된 병원 기록은 아직 없어."
        elif context.medical_overdue:
            answer = f"가장 가까운 병원 일정이 {context.medical_overdue}일 지났어."
        elif context.medical_days_since is not None and context.medical_days_until_next is not None:
            answer = (
                f"최근 병원 기록에서 {context.medical_days_since}일 지났어. "
                f"다음 예정일까지 {context.medical_days_until_next}일 남았어."
            )
        elif context.medical_next_due:
            answer = f"다음 병원 일정은 {context.medical_next_due} 예정이야."
        else:
            answer = "병원 기록은 있지만 다음 일정은 확인할 수 없어."
    elif classification.category == "wake":
        answer = "오늘은 일어난 기록이 있어." if context.wake_recorded else "기록상으로는 잘 모르겠어."
    elif classification.category == "sleep":
        if context.trusted and context.has_ongoing_nap:
            answer = "낮잠잔다고 기록돼 있어."
        else:
            answer = "잠든 기록은 있어." if context.sleep_recorded else "잠든 기록은 아직 없어."
    elif classification.category == "meal":
        answer = "오늘 식사 기록은 있어." if context.meal_recorded else "오늘 식사 기록은 아직 없어."
    elif classification.category == "outing":
        answer = (
            "외출 중인 기록이 있어."
            if context.has_ongoing_outing
            else "외출 기록은 있어."
            if context.outing_recorded
            else "외출 기록은 아직 없어."
        )
    elif classification.category == "work_now":
        answer = "지금은 작업 중인 기록이 있어." if context.is_working_now else "지금 작업 중인 기록은 없어."
    elif classification.category == "work_time":
        answer = "오늘 작업 기록은 있어." if context.work_time_buckets else "오늘 작업 기록은 아직 없어."
    elif classification.category == "completed_today":
        answer = "오늘 끝낸 항목 기록은 있어." if context.completed_count else "오늘 끝낸 항목 기록은 아직 없어."
    elif classification.category == "todo_today":
        answer = "오늘 남은 할 일 기록은 있어." if context.todo_count else "오늘 남은 할 일 기록은 없어."
    elif classification.category == "availability":
        answer = (
            "지금은 바쁜 기록이 있어. 급하면 직접 멘션해봐."
            if context.availability == "busy"
            else "지금은 답할 수 있을지도 몰라."
        )
    elif classification.category == "light_status":
        answer = {
            "working": "작업 중인 기록이 있어.",
            "out": "외출 중인 기록이 있어.",
            "resting": "지금은 쉬는 쪽으로 보여.",
            "unknown": "기록상으로는 잘 모르겠어.",
        }[context.light_status]
    else:
        answer = "기록상으로는 잘 모르겠어."
    limit = max(1, min(int(max_chars), 2000)) if isinstance(max_chars, int) else 300
    return answer[:limit]


def _split_brief_note(text: str) -> tuple[str, str | None]:
    value = " ".join(text.split()).strip()
    if not value.endswith(")"):
        return value, None
    start = value.rfind(" (")
    if start <= 0:
        return value, None
    main, note = value[:start].rstrip(), value[start + 2 : -1].strip()
    if not main or not note:
        return value, None
    return main, note.replace(", ", " · ")


def _truncate_brief_text(lines: list[str], limit: int) -> str:
    selected: list[str] = []
    for line in lines:
        candidate = "\n".join([*selected, line])
        if len(candidate) <= limit:
            selected.append(line)
            continue
        if selected:
            shortened = "\n".join(selected).rstrip()
            return shortened if len(shortened) >= limit else shortened + "…"
        return "…" if limit else ""
    return "\n".join(selected)


def build_group_brief_response(
    context: GroupPublicStatus,
    *,
    max_chars: int = 700,
    detail_level: Literal["safe", "trusted"] = "trusted",
) -> GroupQAResponse:
    """Build trusted-only fallback text and portable rich sections."""

    if detail_level != "trusted" or not context.trusted:
        return GroupQAResponse("단체방 /brief는 trusted 설정에서만 사용할 수 있어.")
    limit = max(1, min(int(max_chars), 4000)) if isinstance(max_chars, int) else 700
    sections: list[dict[str, Any]] = []
    fallback = ["🌤 오늘 브리프", ""]

    wake_text = "일어난 기록이 있어" if context.wake_time else "일어난 기록은 아직 없어"
    sections.append({"title": "기상", "rows": [{"time": context.wake_time, "text": wake_text}]})
    fallback.extend(
        ["기상", f"• {context.wake_time} {wake_text}" if context.wake_time else f"• {wake_text}", ""]
    )
    if context.sleep_time:
        sections.append({"title": "취침", "rows": [{"time": context.sleep_time, "text": "잠든 기록이 있어"}]})
        fallback.extend(["취침", f"• {context.sleep_time} 잠든 기록이 있어", ""])

    meal_rows: list[dict[str, str]] = []
    if context.meal_details:
        for time, item in context.meal_details:
            text, note = _split_brief_note(item)
            row = {"time": time, "text": text}
            if note:
                row["note"] = note
            meal_rows.append(row)
        sections.append({"title": "식사", "rows": meal_rows})
        fallback.append("식사")
        for row in meal_rows:
            fallback.append(f"• {row['time']} {row['text']}")
            if row.get("note"):
                fallback.append(f"  - {row['note']}")
        fallback.append("")
        time, item = context.meal_details[-1]
        last_text, _ = _split_brief_note(item)
        sections.append({"title": "마지막 식사", "rows": [{"time": time, "text": last_text}]})
        fallback.extend(["마지막 식사", f"• {time} {last_text}", ""])
    else:
        sections.append({"title": "식사", "rows": [{"text": "오늘 식사 기록은 아직 없어"}]})
        fallback.extend(["식사", "• 오늘 식사 기록은 아직 없어", ""])

    work_text = "지금은 작업 중인 기록이 있어" if context.is_working_now else "지금은 작업 중인 기록은 없어"
    sections.append({"title": "작업", "rows": [{"text": work_text}]})
    fallback.extend(["작업", f"• {work_text}"])
    if context.work_session_details:
        session_text = "오늘 작업 시간대: " + " · ".join(context.work_session_details)
        sections[-1]["rows"].append({"text": session_text})
        fallback.append(f"• {session_text}")
    fallback.append("")

    if context.completed_count:
        completed_text = f"오늘 끝낸 항목은 {context.completed_count}개 있어"
        sections.append({"title": "완료", "rows": [{"text": completed_text}]})
        fallback.extend(["완료", f"• {completed_text}", ""])
    if context.todo_count:
        todo_text = f"남은 할 일은 {context.todo_count}개 있어"
        sections.append({"title": "할 일", "rows": [{"text": todo_text}]})
        fallback.extend(["할 일", f"• {todo_text}", ""])
    if context.medical_available and context.medical_days_since is not None:
        medical_text = f"D+{context.medical_days_since}"
        if context.medical_overdue:
            medical_text += f" · {context.medical_overdue}일 오버"
        elif context.medical_days_until_next is not None:
            medical_text += f" · 다음 예정일까지 {context.medical_days_until_next}일 남음"
        sections.append({"title": "병원 기록", "rows": [{"text": medical_text}]})
        fallback.extend(["병원 기록", f"• {medical_text}"])

    return GroupQAResponse(
        text=_truncate_brief_text(fallback, limit),
        rich={"kind": "group_qa_brief", "title": "🌤 오늘 브리프", "sections": sections},
    )


def answer_group_brief(
    context: GroupPublicStatus,
    *,
    max_chars: int = 700,
    detail_level: Literal["safe", "trusted"] = "trusted",
) -> str:
    return build_group_brief_response(
        context, max_chars=max_chars, detail_level=detail_level
    ).text
