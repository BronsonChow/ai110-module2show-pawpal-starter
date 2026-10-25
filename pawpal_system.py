"""PawPal+ logic layer.

Classes mirror diagrams/uml.mmd:
- Task: a single care activity (what, when, how often, done or not).
- Pet: pet details plus its list of tasks.
- Owner: manages multiple pets and their free time, and exposes all their tasks.
- Scheduler: the "brain" that retrieves every pet's tasks, picks the ones due
  today, and fits them into the owner's free time by priority and preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum

FREQUENCIES = ("daily", "weekly", "once")


class Priority(Enum):
    """Task priority. The value is the sort score (higher = more important)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _add_minutes(t: time, minutes: int) -> time:
    """Return the time `minutes` after `t` (same day)."""
    return (datetime.combine(date.min, t) + timedelta(minutes=minutes)).time()


@dataclass
class TimeWindow:
    """A block of the day when the owner is free, e.g. 07:00-09:00."""

    start: time
    end: time

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"TimeWindow end {self.end} must be after start {self.start}")

    def minutes(self) -> int:
        """Return the length of this window in minutes."""
        delta = datetime.combine(date.min, self.end) - datetime.combine(date.min, self.start)
        return int(delta.total_seconds() // 60)

    def __str__(self) -> str:
        return f"{self.start:%H:%M}-{self.end:%H:%M}"


@dataclass
class Task:
    """A single pet care item (walk, feeding, meds, enrichment, grooming, ...)."""

    title: str
    category: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    preferred_time: time | None = None
    pet_name: str | None = None  # set by Pet.add_task so the plan knows whose task it is
    frequency: str = "daily"  # "daily" | "weekly" | "once"
    due_date: date | None = None  # used when frequency is "once"
    last_completed: date | None = None

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}, got {self.frequency!r}")

    def mark_complete(self, day: date) -> None:
        """Record that this task was done on the given day."""
        self.last_completed = day

    def is_completed_on(self, day: date) -> bool:
        """Return True if this task was marked complete on the given day."""
        return self.last_completed == day

    def is_due(self, day: date) -> bool:
        """Return True if this task needs doing on the given day (based on frequency)."""
        if self.frequency == "daily":
            return self.last_completed != day
        if self.frequency == "weekly":
            return self.last_completed is None or (day - self.last_completed).days >= 7
        # "once": due on/after its due date until it has been done
        if self.last_completed is not None:
            return False
        return self.due_date is None or self.due_date <= day

    def priority_score(self) -> int:
        """Return a numeric score for sorting (higher = more important)."""
        return self.priority.value


@dataclass
class Pet:
    """A pet and the care tasks attached to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet and set its pet_name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def schedule_walk(self, at: time, duration: int, priority: Priority = Priority.MEDIUM) -> Task:
        """Create a walk task, attach it to this pet, and return it."""
        walk = Task(
            title=f"Walk {self.name}",
            category="walk",
            duration_minutes=duration,
            priority=priority,
            preferred_time=at,
        )
        self.add_task(walk)
        return walk

    def get_tasks(self) -> list[Task]:
        """Return this pet's tasks."""
        return list(self.tasks)


@dataclass
class Owner:
    """The pet owner, their pets, and their scheduling constraints."""

    name: str
    available_windows: list[TimeWindow] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)  # e.g. {"category_order": ["meds", "feeding"]}
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner. Pet names must be unique (tasks refer to pets by name)."""
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet | None:
        """Return the pet with the given name, or None."""
        return next((p for p in self.pets if p.name == name), None)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def total_available_minutes(self) -> int:
        """Return the total free time across all available windows."""
        return sum(w.minutes() for w in self.available_windows)


@dataclass
class ScheduledItem:
    """One entry in a DailyPlan: a task, when it happens, and why."""

    task: Task
    start_time: time | None  # None when the task was skipped
    reason: str

    @property
    def end_time(self) -> time | None:
        if self.start_time is None:
            return None
        return _add_minutes(self.start_time, self.task.duration_minutes)


@dataclass
class DailyPlan:
    """The Scheduler's output: what was scheduled today, what was skipped, and why."""

    date: date
    scheduled: list[ScheduledItem] = field(default_factory=list)
    skipped: list[ScheduledItem] = field(default_factory=list)
    total_minutes: int = 0

    def get_todays_tasks(self) -> list[ScheduledItem]:
        """Return the items scheduled for today, in start-time order."""
        return sorted(self.scheduled, key=lambda item: item.start_time)

    def explain(self) -> str:
        """Return a human-readable explanation of why this plan was chosen."""
        lines = [f"Plan for {self.date:%A %d %b %Y} ({self.total_minutes} min scheduled)"]
        if not self.scheduled:
            lines.append("  Nothing scheduled.")
        for item in self.get_todays_tasks():
            lines.append(
                f"  {item.start_time:%H:%M}-{item.end_time:%H:%M}  {item.task.title}"
                f" [{item.task.pet_name}] - {item.reason}"
            )
        if self.skipped:
            lines.append("Skipped:")
            for item in self.skipped:
                lines.append(f"  {item.task.title} [{item.task.pet_name}] - {item.reason}")
        return "\n".join(lines)


class Scheduler:
    """Builds a DailyPlan from an Owner's tasks and constraints."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Retrieve every task from all of the owner's pets."""
        return self.owner.get_all_tasks()

    def get_due_tasks(self, day: date) -> list[Task]:
        """Retrieve the tasks across all pets that are due on `day`."""
        return [task for task in self.get_all_tasks() if task.is_due(day)]

    def build_daily_plan(self, day: date) -> DailyPlan:
        """Build the plan for `day` in a fixed order of steps:

        1. Keep only tasks that are due on `day`.
        2. Sort them by priority (sort_by_priority).
        3. Place each task into the first time window it fits (fits_in_time);
           tasks that fit nowhere are skipped.
        4. Order the chosen tasks by preference (apply_preferences).
           Preferences never bring back a skipped task.
        """
        plan = DailyPlan(date=day)
        windows = sorted(self.owner.available_windows, key=lambda w: w.start)
        placed: list[list[Task]] = [[] for _ in windows]
        used = [0] * len(windows)

        for task in self.sort_by_priority(self.get_due_tasks(day)):
            for i in self._window_order(task, windows):
                if self.fits_in_time(task, windows[i], used[i]):
                    placed[i].append(task)
                    used[i] += task.duration_minutes
                    break
            else:
                reason = (
                    "no free time windows set"
                    if not windows
                    else f"not enough free time (needs {task.duration_minutes} min)"
                )
                plan.skipped.append(ScheduledItem(task, None, reason))

        for window, tasks in zip(windows, placed):
            start = window.start
            for task in self.apply_preferences(tasks):
                plan.scheduled.append(ScheduledItem(task, start, self._reason(task, window)))
                start = _add_minutes(start, task.duration_minutes)

        plan.total_minutes = sum(item.task.duration_minutes for item in plan.scheduled)
        return plan

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return a new list ordered from highest to lowest priority.

        Ties go to the shorter task, so more tasks fit in the day.
        """
        return sorted(tasks, key=lambda t: (-t.priority_score(), t.duration_minutes))

    def fits_in_time(self, task: Task, window: TimeWindow, minutes_used: int) -> bool:
        """Return True if the task fits in what is left of the given window."""
        return minutes_used + task.duration_minutes <= window.minutes()

    def apply_preferences(self, tasks: list[Task]) -> list[Task]:
        """Return a new list of tasks within one window, ordered by owner preferences.

        Tasks with a preferred time go first, earliest first; ties (and tasks
        without one) follow the owner's "category_order" preference, if any.
        """
        category_order = self.owner.preferences.get("category_order", [])

        def key(task: Task) -> tuple:
            rank = category_order.index(task.category) if task.category in category_order else len(category_order)
            return (task.preferred_time is None, task.preferred_time or time.max, rank)

        return sorted(tasks, key=key)

    def _window_order(self, task: Task, windows: list[TimeWindow]) -> list[int]:
        """Window indexes to try for a task: the one containing its preferred time first."""
        order = list(range(len(windows)))
        if task.preferred_time is not None:
            order.sort(key=lambda i: not (windows[i].start <= task.preferred_time < windows[i].end))
        return order

    def _reason(self, task: Task, window: TimeWindow) -> str:
        """Explain why a task was scheduled where it was."""
        reason = f"{task.priority.name.lower()} priority, fits in {window}"
        if task.preferred_time is not None:
            if window.start <= task.preferred_time < window.end:
                reason += f" (near preferred {task.preferred_time:%H:%M})"
            else:
                reason += f" (preferred {task.preferred_time:%H:%M} had no room)"
        return reason
