"""PawPal+ logic layer.

Classes mirror diagrams/uml.mmd:
- Task: a single care activity (what, when, how often, done or not).
- Pet: pet details plus its list of tasks.
- Owner: manages multiple pets and their free time, and exposes all their tasks.
- Scheduler: the "brain" that retrieves every pet's tasks, picks the ones due
  today, and fits them into the owner's free time by priority and preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum

FREQUENCIES = ("daily", "weekly", "once")
RECURRENCE = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}  # "once" never recurs


class Priority(Enum):
    """Task priority. The value is the sort score (higher = more important)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _add_minutes(t: time, minutes: int) -> time:
    """Return the time `minutes` after `t` (same day)."""
    return (datetime.combine(date.min, t) + timedelta(minutes=minutes)).time()


def _to_minutes(t: time) -> int:
    """Return minutes since midnight."""
    return t.hour * 60 + t.minute


def _from_minutes(minutes: int) -> time:
    """Return the time of day `minutes` after midnight."""
    return time(minutes // 60, minutes % 60)


@dataclass
class TimeWindow:
    """A block of the day when the owner is free, e.g. 07:00-09:00."""

    start: time
    end: time

    def __post_init__(self) -> None:
        """Reject windows that end at or before they start."""
        if self.end <= self.start:
            raise ValueError(f"TimeWindow end {self.end} must be after start {self.start}")

    def minutes(self) -> int:
        """Return the length of this window in minutes."""
        delta = datetime.combine(date.min, self.end) - datetime.combine(date.min, self.start)
        return int(delta.total_seconds() // 60)

    def __str__(self) -> str:
        """Return the window as "HH:MM-HH:MM"."""
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
        """Reject non-positive durations and unknown frequencies."""
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {FREQUENCIES}, got {self.frequency!r}")

    def mark_complete(self, day: date) -> Task | None:
        """Record that this task was done on `day` and return its next occurrence.

        Daily and weekly tasks return a fresh copy due one day / one week after
        `day` (use Pet.complete_task to add it to the pet). "once" tasks return None.
        """
        self.last_completed = day
        step = RECURRENCE.get(self.frequency)
        if step is None:
            return None
        return replace(self, due_date=day + step, last_completed=None)

    def is_completed_on(self, day: date) -> bool:
        """Return True if this task was marked complete on the given day."""
        return self.last_completed == day

    def is_due(self, day: date) -> bool:
        """Return True if this task still needs doing on the given day.

        A task is due from its due date (or right away if it has none) until it
        is marked complete. Recurrence is handled by the next occurrence that
        mark_complete creates, so a completed task is never due again.
        """
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

    def complete_task(self, task: Task, day: date) -> Task | None:
        """Mark one of this pet's tasks done on `day` and add its next occurrence, if any."""
        if task not in self.tasks:
            raise ValueError(f"{task.title!r} is not one of {self.name}'s tasks")
        next_task = task.mark_complete(day)
        if next_task is not None:
            self.add_task(next_task)
        return next_task


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
        """Return when the task finishes, or None if it was skipped."""
        if self.start_time is None:
            return None
        return _add_minutes(self.start_time, self.task.duration_minutes)


@dataclass
class DailyPlan:
    """The Scheduler's output: what was scheduled today, what was skipped, and why."""

    date: date
    scheduled: list[ScheduledItem] = field(default_factory=list)
    skipped: list[ScheduledItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # e.g. clashing preferred times
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
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  {warning}" for warning in self.warnings)
        return "\n".join(lines)


class Scheduler:
    """Builds a DailyPlan from an Owner's tasks and constraints."""

    def __init__(self, owner: Owner) -> None:
        """Create a scheduler for the given owner's pets and free time."""
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Retrieve every task from all of the owner's pets."""
        return self.owner.get_all_tasks()

    def get_due_tasks(self, day: date) -> list[Task]:
        """Retrieve the tasks across all pets that are due on `day`."""
        return [task for task in self.get_all_tasks() if task.is_due(day)]

    def mark_task_complete(self, task: Task, day: date) -> Task | None:
        """Mark a task done on `day` and add its next occurrence to the same pet.

        Daily tasks come back due the next day, weekly tasks a week later;
        "once" tasks don't come back. Returns the new task, or None.
        """
        pet = self.owner.get_pet(task.pet_name)
        if pet is None:
            raise ValueError(f"{task.title!r} doesn't belong to any of {self.owner.name}'s pets")
        return pet.complete_task(task, day)

    def build_daily_plan(self, day: date) -> DailyPlan:
        """Build the plan for `day` in a fixed order of steps:

        1. Keep only tasks that are due on `day`.
        2. Order them by priority; within the same priority, owner preferences
           break ties (order_for_booking).
        3. Book each task, in that order, into a free slot (find_slot): as close
           as possible to its preferred time, otherwise the earliest free gap.
           Tasks with no free gap long enough are skipped.

        Clashing preferred times are recorded as plan warnings (detect_conflicts);
        the booking step itself never double-books a slot.
        """
        plan = DailyPlan(date=day, warnings=self.detect_conflicts(day))
        windows = sorted(self.owner.available_windows, key=lambda w: w.start)
        booked: list[tuple[int, int]] = []  # (start, end) in minutes since midnight

        for task in self.order_for_booking(self.get_due_tasks(day)):
            start = self.find_slot(task, windows, booked)
            if start is None:
                reason = (
                    "no free time windows set"
                    if not windows
                    else f"no free gap of {task.duration_minutes} min left"
                )
                plan.skipped.append(ScheduledItem(task, None, reason))
                continue
            booked.append((_to_minutes(start), _to_minutes(start) + task.duration_minutes))
            plan.scheduled.append(ScheduledItem(task, start, self._reason(task, start)))

        plan.total_minutes = sum(item.task.duration_minutes for item in plan.scheduled)
        return plan

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return a new list ordered by preferred time, earliest first.

        Tasks without a preferred time go last, in their incoming order.
        """
        return sorted(tasks, key=lambda t: (t.preferred_time is None, t.preferred_time or time.max))

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
        day: date | None = None,
    ) -> list[Task]:
        """Return the owner's tasks matching every filter given.

        pet_name: only that pet's tasks.
        completed: True for tasks marked done on `day`, False for tasks still
        pending on `day`. `day` defaults to today.
        """
        day = day or date.today()
        tasks = self.get_all_tasks()
        if pet_name is not None:
            tasks = [t for t in tasks if t.pet_name == pet_name]
        if completed is True:
            tasks = [t for t in tasks if t.is_completed_on(day)]
        elif completed is False:
            tasks = [t for t in tasks if t.is_due(day)]
        return tasks

    def detect_conflicts(self, day: date) -> list[str]:
        """Return a warning for each pair of due tasks whose preferred slots overlap.

        Only tasks with a preferred time can clash. This never raises: the plan
        still gets built, and build_daily_plan moves one of the pair to the
        nearest free slot.
        """
        timed = self.sort_by_time([t for t in self.get_due_tasks(day) if t.preferred_time is not None])
        warnings = []
        for i, first in enumerate(timed):
            first_end = _to_minutes(first.preferred_time) + first.duration_minutes
            for second in timed[i + 1:]:
                if _to_minutes(second.preferred_time) >= first_end:
                    break  # sorted by start, so no later task can overlap `first`
                who = (
                    f"both for {first.pet_name}"
                    if first.pet_name == second.pet_name
                    else f"{first.pet_name} and {second.pet_name}"
                )
                if second.preferred_time == first.preferred_time:
                    clash = f"{first.title} and {second.title} are both at {first.preferred_time:%H:%M}"
                else:
                    clash = (
                        f"{first.title} ({first.preferred_time:%H:%M}, {first.duration_minutes} min)"
                        f" overlaps {second.title} ({second.preferred_time:%H:%M})"
                    )
                warnings.append(f"Conflict: {clash} - {who}")
        return warnings

    def order_for_booking(self, tasks: list[Task]) -> list[Task]:
        """Return a new list in the order build_daily_plan books tasks.

        Highest priority first. Owner preferences only break ties within a
        priority level, so they never outrank priority: tasks with a preferred
        time (earliest first), then the owner's "category_order", then shorter tasks.
        """
        category_order = self.owner.preferences.get("category_order", [])

        def key(task: Task) -> tuple:
            """Sort key: priority, then preferred time, category rank, duration."""
            rank = category_order.index(task.category) if task.category in category_order else len(category_order)
            return (
                -task.priority_score(),
                task.preferred_time is None,
                task.preferred_time or time.max,
                rank,
                task.duration_minutes,
            )

        return sorted(tasks, key=key)

    def fits_in_time(self, task: Task, windows: list[TimeWindow], booked: list[tuple[int, int]]) -> bool:
        """Return True if some free gap in the windows is long enough for the task."""
        return self.find_slot(task, windows, booked) is not None

    def find_slot(self, task: Task, windows: list[TimeWindow], booked: list[tuple[int, int]]) -> time | None:
        """Return the best start time for the task, or None if no free gap is long enough.

        With a preferred time, pick the start closest to it (exactly on it if
        that slot is free). Without one, pick the earliest free gap.
        """
        duration = task.duration_minutes
        target = _to_minutes(task.preferred_time) if task.preferred_time is not None else None
        best: int | None = None
        for window in sorted(windows, key=lambda w: w.start):
            for gap_start, gap_end in self._free_gaps(window, booked):
                if gap_end - gap_start < duration:
                    continue
                if target is None:
                    return _from_minutes(gap_start)
                candidate = min(max(target, gap_start), gap_end - duration)
                if best is None or abs(candidate - target) < abs(best - target):
                    best = candidate
        return None if best is None else _from_minutes(best)

    def _free_gaps(self, window: TimeWindow, booked: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Return the unbooked (start, end) minute ranges inside a window, in order."""
        window_start, window_end = _to_minutes(window.start), _to_minutes(window.end)
        gaps = []
        cursor = window_start
        for booked_start, booked_end in sorted(booked):
            if booked_end <= window_start or booked_start >= window_end:
                continue
            if booked_start > cursor:
                gaps.append((cursor, booked_start))
            cursor = max(cursor, booked_end)
        if cursor < window_end:
            gaps.append((cursor, window_end))
        return gaps

    def _reason(self, task: Task, start: time) -> str:
        """Explain why a task was scheduled when it was."""
        reason = f"{task.priority.name.lower()} priority"
        if task.preferred_time is None:
            return reason + ", earliest free slot"
        if start == task.preferred_time:
            return reason + ", at preferred time"
        return reason + f", nearest free slot to preferred {task.preferred_time:%H:%M}"
