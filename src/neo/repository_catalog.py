from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, TypeAlias

from .errors import ConflictError, NotFoundError

JsonDocument: TypeAlias = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ProjectLocation:
    path: Path
    data: JsonDocument


@dataclass(frozen=True, slots=True)
class TaskLocation:
    project_path: Path
    project: JsonDocument
    milestone: JsonDocument
    task: JsonDocument


@dataclass(frozen=True, slots=True)
class RepositoryCatalog:
    """Read-only lookup projection built from one project repository snapshot."""

    projects: tuple[ProjectLocation, ...]
    project_by_exact_token: Mapping[str, ProjectLocation]
    projects_by_title: Mapping[str, tuple[ProjectLocation, ...]]
    task_by_id: Mapping[str, TaskLocation]
    tasks_by_title: Mapping[str, tuple[TaskLocation, ...]]
    scoped_task_by_id: Mapping[str, Mapping[str, TaskLocation]]
    scoped_tasks_by_title: Mapping[
        str,
        Mapping[str, tuple[TaskLocation, ...]],
    ]

    @classmethod
    def from_locations(
        cls,
        locations: Iterable[ProjectLocation],
    ) -> RepositoryCatalog:
        projects = tuple(locations)
        project_by_exact_token: dict[str, ProjectLocation] = {}
        project_title_lists: dict[str, list[ProjectLocation]] = {}
        task_by_id: dict[str, TaskLocation] = {}
        task_title_lists: dict[str, list[TaskLocation]] = {}
        scoped_task_by_id: dict[str, dict[str, TaskLocation]] = {}
        scoped_task_title_lists: dict[str, dict[str, list[TaskLocation]]] = {}

        for location in projects:
            project = location.data
            project_id = project["project_id"]
            project_by_exact_token.setdefault(project_id, location)
            project_by_exact_token.setdefault(project["slug"], location)
            project_title_lists.setdefault(project["title"].casefold(), []).append(location)

            project_tasks_by_id = scoped_task_by_id.setdefault(project_id, {})
            project_tasks_by_title = scoped_task_title_lists.setdefault(project_id, {})
            for milestone in project["milestones"]:
                for task in milestone["tasks"]:
                    task_location = TaskLocation(
                        project_path=location.path,
                        project=project,
                        milestone=milestone,
                        task=task,
                    )
                    task_id = task["task_id"]
                    task_title = task["title"].casefold()
                    task_by_id.setdefault(task_id, task_location)
                    task_title_lists.setdefault(task_title, []).append(task_location)
                    project_tasks_by_id.setdefault(task_id, task_location)
                    project_tasks_by_title.setdefault(task_title, []).append(task_location)

        return cls(
            projects=projects,
            project_by_exact_token=MappingProxyType(project_by_exact_token),
            projects_by_title=MappingProxyType(
                {
                    title: tuple(matches)
                    for title, matches in project_title_lists.items()
                }
            ),
            task_by_id=MappingProxyType(task_by_id),
            tasks_by_title=MappingProxyType(
                {
                    title: tuple(matches)
                    for title, matches in task_title_lists.items()
                }
            ),
            scoped_task_by_id=MappingProxyType(
                {
                    project_id: MappingProxyType(project_tasks)
                    for project_id, project_tasks in scoped_task_by_id.items()
                }
            ),
            scoped_tasks_by_title=MappingProxyType(
                {
                    project_id: MappingProxyType(
                        {
                            title: tuple(matches)
                            for title, matches in title_lists.items()
                        }
                    )
                    for project_id, title_lists in scoped_task_title_lists.items()
                }
            ),
        )

    def resolve_project(self, token: str) -> ProjectLocation:
        exact = self.project_by_exact_token.get(token)
        if exact is not None:
            return exact
        matches = self.projects_by_title.get(token.casefold(), ())
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ConflictError(f"Project title is ambiguous: {token}")
        raise NotFoundError(f"Project not found: {token}")

    def resolve_task(
        self,
        token: str,
        project_token: str | None = None,
    ) -> TaskLocation:
        if project_token is None:
            exact = self.task_by_id.get(token)
            matches = self.tasks_by_title.get(token.casefold(), ())
        else:
            project = self.resolve_project(project_token)
            project_id = project.data["project_id"]
            exact = self.scoped_task_by_id.get(project_id, {}).get(token)
            matches = self.scoped_tasks_by_title.get(project_id, {}).get(
                token.casefold(),
                (),
            )

        if exact is not None:
            return exact
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ConflictError(f"Task title is ambiguous: {token}")
        raise NotFoundError(f"Task not found: {token}")


def resolve_milestone(project: JsonDocument, token: str) -> JsonDocument:
    token_lower = token.casefold()
    matches = [
        milestone
        for milestone in project["milestones"]
        if milestone["milestone_id"] == token
        or milestone["title"].casefold() == token_lower
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ConflictError(f"Milestone title is ambiguous: {token}")
    raise NotFoundError(f"Milestone not found: {token}")
