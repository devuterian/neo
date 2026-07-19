from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .brief_projection import BriefProjection, build_brief_projection

STATUS_KO = {
    "draft": "초안",
    "active": "진행 중",
    "waiting": "외부 대기",
    "paused": "내 사유로 중단",
    "complete": "완료",
    "cancelled": "취소",
    "todo": "할 일",
    "in_progress": "진행 중",
    "done": "완료",
    "planned": "예정",
    "closed": "종료",
    "void": "무효",
}

MEAL_TAG_KO = {
    "breakfast": "아침",
    "lunch": "점심",
    "dinner": "저녁",
    "snack": "간식",
}


def render_brief(
    *,
    project_docs: Iterable[tuple[Path, dict[str, Any]]],
    day_docs: Iterable[tuple[Path, dict[str, Any]]],
    calendar_index: dict[str, Any],
    medical: dict[str, Any] | None = None,
    pending: dict[str, Any] | None = None,
) -> str:
    """Build the shared projection once, then render the human Markdown view."""

    projection = build_brief_projection(
        project_docs=project_docs,
        day_docs=day_docs,
        calendar_index=calendar_index,
        medical=medical,
        pending=pending,
    )
    return render_brief_projection(projection)


def render_brief_projection(projection: BriefProjection) -> str:
    """Render brief.md without re-reading canonical documents."""

    lines = [
        "<!-- GENERATED FILE. DO NOT EDIT DIRECTLY. -->",
        "<!-- Sources: data/projects, data/days, data/indexes/calendar.json -->",
        "",
        "# 브리프",
        "",
        f"- Generated: `{projection.generated_at}`",
    ]

    medical = projection.medical
    if medical is not None:
        lines.extend(["", "## 병원 기록", ""])
        lines.append(f"- 최근 기록 후 {medical.days_since if medical.days_since is not None else '?'}일")
        if medical.last_date:
            lines.append(f"- 마지막 기록: {medical.last_date}")
        if medical.next_due:
            lines.append(f"- 다음 일정: {medical.next_due}")
        if medical.overdue > 0:
            lines.append(f"- ⚠️ **{medical.overdue}일 오버**")
        elif medical.next_due and medical.days_until_next is not None and medical.days_until_next <= 3:
            lines.append(f"- ⏰ 다음 일정까지 **{medical.days_until_next}일** 남음")
        if medical.note:
            lines.append(f"- {medical.note}")

    active_pending = [item for item in projection.pending_items if not item.done]
    done_pending = [item for item in projection.pending_items if item.done]
    if active_pending or done_pending:
        lines.extend(["", "## 밀린 일 (Pending)", ""])
        for item in [*active_pending, *done_pending]:
            lines.append(f"- [{'x' if item.done else ' '}] {item.title}")
            if item.description:
                lines.append(f"  {item.description}")

    lines.extend(["", "## 현재 생활일", ""])
    current_day = projection.current_day
    if current_day is None:
        lines.append("- 활성 생활일이 없어.")
    else:
        lines.extend(
            [
                f"- 기상일: `{current_day.date}`",
                f"- 기상: `{current_day.wake_at}`",
                f"- 취침: `{current_day.sleep_at or '미기록'}`",
                f"- 오늘 작업 형태: `{_capacity_text(current_day.workday_capacity)}`",
                f"- 상태: `{STATUS_KO.get(current_day.status, current_day.status)}`",
            ]
        )

        if current_day.mood is not None:
            lines.extend(["", "### 기분", ""])
            lines.append(f"- {current_day.mood.summary}")
            if current_day.mood.reason:
                lines.append(f"  이유: {current_day.mood.reason}")

        if current_day.meals:
            lines.extend(["", "### 식사", ""])
            for meal in current_day.meals:
                tag_ko = MEAL_TAG_KO.get(meal.tag, meal.tag)
                lines.append(f"- {tag_ko}: {meal.what} (`{meal.occurred_at}`)")

        if current_day.medications:
            lines.extend(["", "### 약 복용", ""])
            for medication in current_day.medications:
                if medication.action == "taken":
                    status = "✅"
                elif medication.action == "skipped":
                    status = "⏭"
                else:
                    status = "❓"
                time_text = f" (`{medication.occurred_at}`)" if medication.occurred_at else " (시각 미상)"
                dose_text = f" — {medication.dose}" if medication.dose else ""
                note_text = f" — {medication.note}" if medication.note else ""
                lines.append(f"- {status} {medication.name}{dose_text}{time_text}{note_text}")

        if current_day.outings:
            lines.extend(["", "### 외출", ""])
            for outing in current_day.outings:
                returned = f"→ `{outing.returned_at}`" if outing.returned_at else "아직 안 돌아옴"
                purpose = f" ({outing.purpose})" if outing.purpose else ""
                lines.append(f"- {outing.place}{purpose} — 나감 `{outing.left_at}`, {returned}")

        if current_day.todos:
            lines.extend(["", "### 오늘 할 일", ""])
            for item in current_day.todos:
                lines.append(f"- [{'x' if item.done else ' '}] {item.title}")
                if item.description:
                    lines.append(f"  {item.description}")

        lines.extend(["", "## 오늘 계획과 작업", ""])
        if current_day.work_plan:
            for item in current_day.work_plan:
                lines.append(
                    f"- **{item.project_title}** / "
                    f"{item.milestone_title} / "
                    f"{item.task_title} "
                    f"— {STATUS_KO.get(item.task_status, item.task_status)}"
                )
        else:
            lines.append("- 계획된 프로젝트 태스크가 없어.")

        if current_day.open_work_session is not None:
            session = current_day.open_work_session
            lines.append(
                f"- 현재 작업 세션: **{session.task_title}**, "
                f"체크인 `{session.checked_in_at}`"
            )
        elif current_day.recorded_work_minutes is not None:
            lines.append(f"- 기록된 작업 시간: 약 `{current_day.recorded_work_minutes}` 분")

        if current_day.external_schedule:
            lines.extend(["", "### 외부 일정 스냅샷", ""])
            for event in current_day.external_schedule:
                lines.append(f"- {event.title}: `{event.starts_at}` → `{event.ends_at}`")

    lines.extend(["", "## 프로젝트", ""])
    if not projection.projects:
        lines.append("- 열린 프로젝트가 없어.")
    else:
        for project in projection.projects:
            lines.append(f"### {project.title}")
            lines.append("")
            lines.append(f"- 상태: `{STATUS_KO.get(project.status, project.status)}`")
            if project.status == "waiting" and project.waiting_on:
                lines.append(f"- 대기 대상: {project.waiting_on}")
            if project.status == "paused" and project.pause_reason:
                lines.append(f"- 중단 이유: {project.pause_reason}")
            milestone = project.current_milestone
            if milestone is not None:
                lines.append(f"- 현재 마일스톤: {milestone.title}")
                lines.append(f"- 남은 작업량: `{milestone.remaining_effort}`")
                lines.append(f"- 마일스톤 날짜: {_calendar_text(milestone.calendar_time)}")
                if milestone.open_tasks:
                    lines.append("- 열린 태스크:")
                    for task in milestone.open_tasks:
                        lines.append(f"  - {task.title} — {STATUS_KO.get(task.status, task.status)}")
            lines.append(f"- 최종 납기: {_calendar_text(project.deadline_time)}")
            lines.append("")

    lines.extend(["## Calendar 상태", ""])
    lines.append(f"- 조회 상태: `{projection.calendar.status}`")
    lines.append(f"- 마지막 조회: `{projection.calendar.fetched_at or '미조회'}`")
    if projection.calendar.error:
        lines.append(f"- 오류: {projection.calendar.error}")
    lines.append("")
    return "\n".join(lines)


def _capacity_text(value: Any) -> str:
    if value is None:
        return "아직 정하지 않음"
    mapping = {
        1: "프로젝트 작업을 주된 일정으로 삼는 날",
        0.5: "외부 일정과 프로젝트 작업을 병행하는 날",
        0: "프로젝트 작업을 계획하지 않는 날",
    }
    return mapping[value]


def _calendar_text(value: str) -> str:
    return f"`{value}`" if "T" in value else value
