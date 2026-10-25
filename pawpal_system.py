"""PawPal+ logic layer.

Class skeletons that mirror diagrams/uml.mmd. Method bodies are stubs to be
filled in during implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Task:
    """A single pet care item (walk, feeding, meds, enrichment, grooming, ...)."""

    title: str
    category: str
    duration_minutes: int
    priority: str = "medium"  # "low" | "medium" | "high"
    preferred_time: str | None = None  # e.g. "08:00" or "morning"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        raise NotImplementedError

    def priority_score(self) -> int:
        """Return a numeric score for sorting (higher = more important)."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the care tasks attached to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        raise NotImplementedError

    def schedule_walk(self, time: str, duration: int, priority: str = "medium") -> Task:
        """Create a walk task, attach it to this pet, and return it."""
        raise NotImplementedError

    def get_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner, their pets, and their scheduling constraints."""

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner."""
        raise NotImplementedError

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        raise NotImplementedError


@dataclass
class DailyPlan:
    """The Scheduler's output: what was scheduled today, what was skipped, and why."""

    date: date
    scheduled: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def get_todays_tasks(self) -> list[Task]:
        """Return the tasks scheduled for today, in order."""
        raise NotImplementedError

    def explain(self) -> str:
        """Return a human-readable explanation of why this plan was chosen."""
        raise NotImplementedError


class Scheduler:
    """Builds a DailyPlan from an Owner's tasks and constraints."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def build_daily_plan(self) -> DailyPlan:
        """Choose and order today's tasks based on time, priority, and preferences."""
        raise NotImplementedError

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered from highest to lowest priority."""
        raise NotImplementedError

    def fits_in_time(self, task: Task, minutes_left: int) -> bool:
        """Return True if the task fits in the remaining available time."""
        raise NotImplementedError

    def apply_preferences(self, tasks: list[Task]) -> list[Task]:
        """Adjust task order/selection using the owner's preferences."""
        raise NotImplementedError
