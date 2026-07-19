from __future__ import annotations

import argparse
from pathlib import Path

from .domain import fridge as fridge_domain
from .domain import private_spark as spark_domain
from .domain import projects as project_domain
from .mutations import resource_names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="neoctl")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--auto-wake",
        choices=["never", "ask", "always"],
        help="Override auto_wake policy from config/app.json",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Validate the repository and rebuild derived files")
    sub.add_parser("validate", help="Validate schemas, IDs, references, and indexes")
    sub.add_parser("migrate", help="Migrate existing state to current schemas")
    sub.add_parser("doctor", help="Run repository diagnostics")

    message = sub.add_parser("message")
    msg_sub = message.add_subparsers(dest="message_command", required=True)
    message_log = msg_sub.add_parser("log")
    message_log.add_argument(
        "--role",
        required=True,
        choices=["user", "assistant", "system", "tool"],
    )
    message_log.add_argument("--content", required=True)
    message_log.add_argument("--at", required=True)

    index = sub.add_parser("index", help="Manage generated indexes")
    index_sub = index.add_subparsers(dest="index_command", required=True)
    index_sub.add_parser("rebuild")

    brief = sub.add_parser("brief", help="Manage brief.md")
    brief_sub = brief.add_subparsers(dest="brief_command", required=True)
    brief_sub.add_parser("render")

    project = sub.add_parser("project")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    create = project_sub.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--slug")
    create.add_argument("--description", default="")
    create.add_argument("--approve", action="store_true")
    project_sub.add_parser("list")
    show = project_sub.add_parser("show")
    show.add_argument("project")
    rename = project_sub.add_parser("rename")
    rename.add_argument("project")
    rename.add_argument("--title")
    rename.add_argument("--slug")
    rename.add_argument("--approve", action="store_true")
    status = project_sub.add_parser("status")
    status.add_argument("project")
    status.add_argument("status", choices=sorted(project_domain.PROJECT_STATUSES))
    status.add_argument("--reason")
    status.add_argument("--waiting-on")
    status.add_argument("--next-review-at")
    status.add_argument("--pause-reason")
    status.add_argument("--resume-condition")
    status.add_argument("--approve", action="store_true")
    deadline = project_sub.add_parser("link-deadline")
    deadline.add_argument("project")
    deadline.add_argument("--event-id")
    decision = project_sub.add_parser("decision")
    decision.add_argument("project")
    decision.add_argument("--title", required=True)
    decision.add_argument("--detail", required=True)
    decision.add_argument("--approve", action="store_true")

    milestone = sub.add_parser("milestone")
    milestone_sub = milestone.add_subparsers(dest="milestone_command", required=True)
    milestone_add = milestone_sub.add_parser("add")
    milestone_add.add_argument("project")
    milestone_add.add_argument("--title", required=True)
    milestone_add.add_argument("--remaining-effort", required=True, type=float)
    milestone_add.add_argument("--approve", action="store_true")
    milestone_status = milestone_sub.add_parser("status")
    milestone_status.add_argument("project")
    milestone_status.add_argument("milestone")
    milestone_status.add_argument(
        "status",
        choices=sorted(project_domain.MILESTONE_STATUSES),
    )
    milestone_status.add_argument("--approve", action="store_true")
    milestone_effort = milestone_sub.add_parser("effort")
    milestone_effort.add_argument("project")
    milestone_effort.add_argument("milestone")
    milestone_effort.add_argument("value", type=float)
    milestone_effort.add_argument("--approve", action="store_true")
    milestone_link = milestone_sub.add_parser("link-calendar")
    milestone_link.add_argument("project")
    milestone_link.add_argument("milestone")
    milestone_link.add_argument("--event-id")

    task = sub.add_parser("task")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_list = task_sub.add_parser("list")
    task_list.add_argument("--project")
    task_list.add_argument("--status", choices=sorted(project_domain.TASK_STATUSES))
    task_add = task_sub.add_parser("add")
    task_add.add_argument("project")
    task_add.add_argument("milestone")
    task_add.add_argument("--title", required=True)
    task_status = task_sub.add_parser("status")
    task_status.add_argument("task")
    task_status.add_argument("status", choices=sorted(project_domain.TASK_STATUSES))
    task_status.add_argument("--project")
    task_status.add_argument("--waiting-on")
    task_note = task_sub.add_parser("note")
    task_note.add_argument("task")
    task_note.add_argument("--project")
    task_note.add_argument("--text", required=True)

    day = sub.add_parser("day")
    day.add_argument(
        "--date",
        help=(
            "Target a specific life day by date (YYYY-MM-DD) instead of the "
            "current active day"
        ),
    )
    day_sub = day.add_subparsers(dest="day_command", required=True)
    wake = day_sub.add_parser("wake")
    wake.add_argument("--at")
    capacity = day_sub.add_parser("capacity")
    capacity.add_argument("value", type=float)
    plan = day_sub.add_parser("work-plan-task")
    plan.add_argument("task")
    plan.add_argument("--project")
    plan.add_argument("--allocation", type=float, required=True)
    plan.add_argument("--calendar-event-id")
    snapshot = day_sub.add_parser("snapshot-calendar")
    snapshot.add_argument("--event-id", action="append", default=[])
    correct = day_sub.add_parser("correct")
    correct.add_argument("--field", required=True, choices=["wake_at", "sleep_at", "status", "workday_capacity"])
    correct.add_argument("--value", required=True)
    correct.add_argument("--reason", required=True)
    correct.add_argument("--expected-revision")
    sleep = day_sub.add_parser("sleep")
    sleep.add_argument("--at")
    sleep.add_argument(
        "--clear",
        action="store_true",
        help="Clear a previously recorded sleep time",
    )
    nap = day_sub.add_parser("nap")
    nap_sub = nap.add_subparsers(dest="nap_command", required=True)
    nap_go = nap_sub.add_parser("go")
    nap_go.add_argument("--at")
    nap_back = nap_sub.add_parser("back")
    nap_back.add_argument("nap")
    nap_back.add_argument("--at")
    nap_remove = nap_sub.add_parser("remove")
    nap_remove.add_argument("nap")
    nap_edit = nap_sub.add_parser("edit")
    nap_edit.add_argument("nap")
    nap_edit.add_argument("--started-at")
    nap_edit.add_argument("--ended-at")
    note = day_sub.add_parser("note")
    note.add_argument("--text", required=True)
    void = day_sub.add_parser("void")
    void.add_argument("--approve", action="store_true")
    reopen = day_sub.add_parser("reopen")
    reopen.add_argument("--approve", action="store_true")

    todo = day_sub.add_parser("todo")
    todo_sub = todo.add_subparsers(dest="todo_command", required=True)
    todo_add = todo_sub.add_parser("add")
    todo_add.add_argument("--title", required=True)
    todo_add.add_argument("--description", default="")
    todo_done = todo_sub.add_parser("done")
    todo_done.add_argument("todo")
    todo_undo = todo_sub.add_parser("undo")
    todo_undo.add_argument("todo")
    todo_remove = todo_sub.add_parser("remove")
    todo_remove.add_argument("todo")

    meal = day_sub.add_parser("meal")
    meal_sub = meal.add_subparsers(dest="meal_command", required=True)
    meal_add = meal_sub.add_parser("add")
    meal_add.add_argument(
        "--tag",
        required=True,
        choices=["breakfast", "lunch", "dinner", "snack"],
    )
    meal_add.add_argument("--what", required=True)
    meal_add.add_argument("--at")
    meal_remove = meal_sub.add_parser("remove")
    meal_remove.add_argument("meal")

    mood = day_sub.add_parser("mood")
    mood_sub = mood.add_subparsers(dest="mood_command", required=True)
    mood_set = mood_sub.add_parser("set")
    mood_set.add_argument("--summary", required=True)
    mood_set.add_argument("--reason")
    mood_sub.add_parser("clear")

    outing = day_sub.add_parser("outing")
    outing_sub = outing.add_subparsers(dest="outing_command", required=True)
    outing_go = outing_sub.add_parser("go")
    outing_go.add_argument("--place", required=True)
    outing_go.add_argument("--purpose")
    outing_go.add_argument("--at")
    outing_back = outing_sub.add_parser("back")
    outing_back.add_argument("outing")
    outing_back.add_argument("--at")
    outing_remove = outing_sub.add_parser("remove")
    outing_remove.add_argument("outing")

    medication = day_sub.add_parser("med")
    medication_sub = medication.add_subparsers(dest="med_command", required=True)
    medication_take = medication_sub.add_parser("take")
    medication_take.add_argument("--name", required=True)
    medication_take.add_argument("--at")
    medication_take.add_argument("--dose")
    medication_take.add_argument("--note")
    medication_skip = medication_sub.add_parser("skip")
    medication_skip.add_argument("--name", required=True)
    medication_skip.add_argument("--at")
    medication_skip.add_argument("--reason")
    medication_remove = medication_sub.add_parser("remove")
    medication_remove.add_argument("medication_id")
    medication_sub.add_parser("status")
    medication_history = medication_sub.add_parser(
        "history",
        help="Read medication events across all life days",
    )
    medication_history.add_argument("--name")
    medication_history.add_argument("--limit", type=int)
    medication_history.add_argument("--action", choices=["taken", "skipped"])
    medication_history.add_argument("--since")
    medication_history.add_argument("--until")

    shower = day_sub.add_parser("shower")
    shower_sub = shower.add_subparsers(dest="shower_command", required=True)
    shower_go = shower_sub.add_parser("go")
    shower_go.add_argument("--type", choices=["shower", "bath"], default="shower")
    shower_go.add_argument("--at")
    shower_back = shower_sub.add_parser("back")
    shower_back.add_argument("shower")
    shower_back.add_argument("--at")
    shower_remove = shower_sub.add_parser("remove")
    shower_remove.add_argument("shower")

    hair_dry = day_sub.add_parser("hair-dry")
    hair_dry_sub = hair_dry.add_subparsers(dest="hair_dry_command", required=True)
    hair_dry_go = hair_dry_sub.add_parser("go")
    hair_dry_go.add_argument("--at")
    hair_dry_back = hair_dry_sub.add_parser("back")
    hair_dry_back.add_argument("hair_dry")
    hair_dry_back.add_argument("--at")
    hair_dry_remove = hair_dry_sub.add_parser("remove")
    hair_dry_remove.add_argument("hair_dry")

    work = sub.add_parser("work")
    work_sub = work.add_subparsers(dest="work_command", required=True)
    check_in = work_sub.add_parser("check-in")
    check_in.add_argument("task")
    check_in.add_argument("--project")
    check_in.add_argument("--at")
    check_out = work_sub.add_parser("check-out")
    check_out.add_argument("--at")
    check_out.add_argument("--note")
    check_out.add_argument(
        "--task-status",
        choices=["in_progress", "waiting", "done"],
    )
    check_out.add_argument("--waiting-on")

    calendar = sub.add_parser("calendar")
    calendar_sub = calendar.add_subparsers(dest="calendar_command", required=True)
    calendar_import = calendar_sub.add_parser("import-index")
    calendar_import.add_argument("--input", required=True, type=Path)
    unavailable = calendar_sub.add_parser("mark-unavailable")
    unavailable.add_argument("--error", required=True)
    calendar_sub.add_parser("show")
    refresh = calendar_sub.add_parser("refresh")
    refresh.add_argument("--range-weeks", type=int, default=6)

    medical = sub.add_parser("medical")
    medical_sub = medical.add_subparsers(dest="medical_command", required=True)
    medical_sub.add_parser("list")
    medical_add = medical_sub.add_parser("add")
    medical_add.add_argument("--provider", required=True, help="Hospital or clinic name")
    medical_add.add_argument("--title", required=True, help="Treatment, examination, or follow-up name")
    medical_add.add_argument("--at", required=True, help="Most recent date (YYYY-MM-DD)")
    medical_add.add_argument("--cycle-days", type=int, help="Optional recurrence interval")
    medical_add.add_argument("--kind")
    medical_add.add_argument("--note")
    medical_record = medical_sub.add_parser("record")
    medical_record.add_argument("medical_id")
    medical_record.add_argument("--at", help="Date (YYYY-MM-DD), default today")
    medical_record.add_argument("--note")
    medical_remove = medical_sub.add_parser("remove")
    medical_remove.add_argument("medical_id")
    medical_remove.add_argument("--approve", action="store_true")

    pending = sub.add_parser("pending")
    pending_sub = pending.add_subparsers(dest="pending_command", required=True)
    pending_add = pending_sub.add_parser("add")
    pending_add.add_argument("--title", required=True)
    pending_add.add_argument("--description", default="")
    pending_add.add_argument("--carried-from")
    pending_done = pending_sub.add_parser("done")
    pending_done.add_argument("pending")
    pending_undo = pending_sub.add_parser("undo")
    pending_undo.add_argument("pending")
    pending_remove = pending_sub.add_parser("remove")
    pending_remove.add_argument("pending")
    pending_sub.add_parser("list")

    someday = sub.add_parser("someday", help="Manage optional someday items")
    someday_sub = someday.add_subparsers(dest="someday_command", required=True)
    someday_list = someday_sub.add_parser("list")
    someday_list.add_argument("--all", action="store_true")
    someday_add = someday_sub.add_parser("add")
    someday_add.add_argument("--title", required=True)
    someday_add.add_argument("--description", default="")
    someday_done = someday_sub.add_parser("done")
    someday_done.add_argument("someday")
    someday_undo = someday_sub.add_parser("undo")
    someday_undo.add_argument("someday")
    someday_remove = someday_sub.add_parser("remove")
    someday_remove.add_argument("someday")

    resource = sub.add_parser(
        "resource",
        help="Typed CRUD for authoritative workspace resources",
    )
    resource_sub = resource.add_subparsers(dest="resource_command", required=True)
    capabilities = resource_sub.add_parser("capabilities")
    capabilities.add_argument("resource", nargs="?", choices=resource_names())
    get = resource_sub.add_parser("get")
    get.add_argument("resource", choices=resource_names())
    get.add_argument("target", nargs="?")
    listing = resource_sub.add_parser("list")
    listing.add_argument("resource", choices=resource_names())
    resource_add = resource_sub.add_parser("add")
    resource_add.add_argument("resource", choices=resource_names())
    resource_add.add_argument("--title")
    resource_add.add_argument("--description", default="")
    resource_add.add_argument("--slug")
    resource_add.add_argument("--wake-at")
    resource_add.add_argument("--last-injection")
    resource_add.add_argument("--cycle-days", type=int)
    resource_add.add_argument("--days-since", type=int)
    resource_add.add_argument("--name")
    resource_add.add_argument("--category")
    resource_add.add_argument("--quantity")
    resource_add.add_argument("--location")
    resource_add.add_argument("--expires-at")
    resource_add.add_argument("--notes", default="")
    resource_add.add_argument("--source", default="")
    resource_add.add_argument("--ordered-at")
    resource_add.add_argument("--expected-at")
    resource_add.add_argument("--carried-from-day-id")
    for action_name in ("update", "correct"):
        mutation = resource_sub.add_parser(action_name)
        mutation.add_argument("resource", choices=resource_names())
        mutation.add_argument("target")
        mutation.add_argument("--field", required=True)
        mutation.add_argument("--value", required=True)
        mutation.add_argument("--reason")
        mutation.add_argument("--expected-revision")
    resource_delete = resource_sub.add_parser("delete")
    resource_delete.add_argument("resource", choices=resource_names())
    resource_delete.add_argument("target")
    resource_delete.add_argument("--reason", required=True)
    resource_delete.add_argument("--confirm", action="store_true")
    fridge = sub.add_parser("fridge", help="Manage food inventory")
    fridge_sub = fridge.add_subparsers(dest="fridge_command", required=True)
    fridge_add = fridge_sub.add_parser("add")
    fridge_add.add_argument("--name", required=True)
    fridge_add.add_argument(
        "--category",
        default="other",
        choices=sorted(fridge_domain.CATEGORIES),
    )
    fridge_add.add_argument("--quantity")
    fridge_add.add_argument(
        "--location",
        default="pantry",
        choices=sorted(fridge_domain.LOCATIONS),
    )
    fridge_add.add_argument("--expires")
    fridge_add.add_argument("--notes", default="")
    fridge_add.add_argument("--source", default="")
    fridge_add.add_argument("--ordered-at")
    fridge_add.add_argument("--expected-at")
    fridge_arrive = fridge_sub.add_parser("arrive")
    fridge_arrive.add_argument("item_id", nargs="?", help="Item ID, or omit for --all")
    fridge_arrive.add_argument(
        "--all",
        action="store_true",
        help="Arrive all in-transit items",
    )
    fridge_arrive.add_argument(
        "--location",
        default="freezer",
        choices=["fridge", "freezer", "pantry", "shelf", "counter"],
    )
    fridge_consume = fridge_sub.add_parser("consume")
    fridge_consume.add_argument("item_id")
    fridge_consume.add_argument("--quantity")
    fridge_remove = fridge_sub.add_parser("remove")
    fridge_remove.add_argument("item_id")
    fridge_list = fridge_sub.add_parser("list")
    fridge_list.add_argument("--location", choices=sorted(fridge_domain.LOCATIONS))
    fridge_list.add_argument("--category", choices=sorted(fridge_domain.CATEGORIES))
    fridge_list.add_argument(
        "--all",
        action="store_true",
        help="Include consumed items",
    )
    fridge_sub.add_parser("expired")
    fridge_sub.add_parser("transit")

    private = sub.add_parser("private", help="Manage private-only records")
    private_sub = private.add_subparsers(dest="private_command", required=True)
    spark = private_sub.add_parser("spark", help="Manage private spark records")
    spark_sub = spark.add_subparsers(dest="spark_command", required=True)

    spark_log = spark_sub.add_parser("log")
    spark_log.add_argument("--kind", required=True, choices=sorted(spark_domain.KINDS))
    spark_log.add_argument("--partner")
    spark_log.add_argument("--started-at")
    spark_log.add_argument("--ended-at")
    spark_log.add_argument("--life-day")
    spark_log.add_argument("--mood")
    spark_log.add_argument("--condition")
    spark_log.add_argument("--discomfort")
    spark_log.add_argument("--note")
    spark_log.add_argument("--allow-imprecise", action="store_true")

    spark_list = spark_sub.add_parser("list")
    spark_list.add_argument("--month")
    spark_list.add_argument("--life-day")
    spark_list.add_argument("--last")
    spark_list.add_argument("--include-notes", action="store_true")
    spark_list.add_argument("--json", action="store_true", dest="spark_json")

    spark_edit = spark_sub.add_parser("edit")
    spark_edit.add_argument("record_id")
    spark_edit.add_argument("--kind", choices=sorted(spark_domain.KINDS))
    spark_edit.add_argument("--partner")
    spark_edit.add_argument("--started-at")
    spark_edit.add_argument("--ended-at")
    spark_edit.add_argument("--mood")
    spark_edit.add_argument("--condition")
    spark_edit.add_argument("--discomfort")
    spark_edit.add_argument("--note")

    spark_remove = spark_sub.add_parser("remove")
    spark_remove.add_argument("record_id")
    spark_remove.add_argument("--approve", action="store_true")

    spark_report = spark_sub.add_parser("report")
    spark_report.add_argument("--month")
    spark_report.add_argument("--life-day")
    spark_report.add_argument("--last")
    spark_report.add_argument("--output", type=Path)
    spark_report.add_argument("--include-notes", action="store_true")

    return parser
