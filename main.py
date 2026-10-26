"""Demo script: build an owner with two pets, print today's schedule, then show
sorting, filtering, recurring tasks and conflict warnings."""

from datetime import date, time, timedelta

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TimeWindow


def print_tasks(heading: str, tasks: list[Task], day: date) -> None:
    """Print a heading and one line per task: time, title, pet, status."""
    print(f"\n{heading}")
    if not tasks:
        print("  (none)")
    for task in tasks:
        when = f"{task.preferred_time:%H:%M}" if task.preferred_time else "any time"
        if task.is_completed_on(day):
            status = "done"
        elif task.is_due(day):
            status = "pending"
        elif task.last_completed is None:
            status = f"next due {task.due_date:%a %d %b}"
        else:
            status = f"done {task.last_completed:%a %d %b}"
        print(f"  {when:<9} {task.title:<18} {task.pet_name:<8} {status}")


def main() -> None:
    owner = Owner(
        name="Sam",
        available_windows=[
            TimeWindow(time(7, 0), time(9, 0)),
            TimeWindow(time(17, 30), time(19, 0)),
        ],
        preferences={"category_order": ["meds", "feeding"]},
    )

    biscuit = Pet("Biscuit", "dog", age=4)
    mochi = Pet("Mochi", "cat", age=7)
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    # Added deliberately out of time order, so sort_by_time has work to do
    biscuit.add_task(Task("Evening walk", "walk", 40, Priority.MEDIUM, preferred_time=time(18, 0)))
    mochi.add_task(Task("Brushing", "grooming", 20, Priority.LOW, frequency="weekly"))
    mochi.add_task(Task("Thyroid pill", "meds", 5, Priority.HIGH, preferred_time=time(8, 0)))
    biscuit.schedule_walk(at=time(7, 30), duration=30, priority=Priority.HIGH)
    mochi.add_task(Task("Feather toy play", "enrichment", 15, Priority.LOW, preferred_time=time(17, 30)))
    biscuit.add_task(Task("Breakfast", "feeding", 10, Priority.HIGH, preferred_time=time(7, 0)))
    # Clashes with Biscuit's 07:30 walk on purpose, to show a conflict warning
    mochi.add_task(Task("Litter box", "other", 10, Priority.MEDIUM, preferred_time=time(7, 45)))

    today = date.today()
    scheduler = Scheduler(owner)

    # --- Sorting ---
    all_tasks = scheduler.get_all_tasks()
    print_tasks("Tasks as added (unsorted):", all_tasks, today)
    print_tasks("Sorted by time (sort_by_time):", scheduler.sort_by_time(all_tasks), today)

    # --- Mark a couple of tasks done so the status filters have something to show ---
    breakfast = next(t for t in biscuit.get_tasks() if t.title == "Breakfast")
    pill = next(t for t in mochi.get_tasks() if t.title == "Thyroid pill")
    next_breakfast = scheduler.mark_task_complete(breakfast, today)
    scheduler.mark_task_complete(pill, today)
    print(f"\nCompleted {breakfast.title} and {pill.title}; next breakfast due {next_breakfast.due_date:%A %d %b}")

    # --- Filtering (results sorted by time for readability) ---
    print_tasks("Biscuit's tasks (pet_name='Biscuit'):",
                scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Biscuit")), today)
    print_tasks("Mochi's tasks (pet_name='Mochi'):",
                scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi")), today)
    print_tasks("Done today (completed=True):",
                scheduler.sort_by_time(scheduler.filter_tasks(completed=True, day=today)), today)
    print_tasks("Still pending today (completed=False):",
                scheduler.sort_by_time(scheduler.filter_tasks(completed=False, day=today)), today)
    print_tasks("Mochi's pending tasks (pet_name='Mochi', completed=False):",
                scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi", completed=False, day=today)), today)
    print(f"\nNext breakfast due tomorrow: {next_breakfast.is_due(today + timedelta(days=1))}")

    # --- Today's schedule for what's still pending ---
    plan = scheduler.build_daily_plan(today)
    print(f"\nToday's Schedule - {plan.date:%A, %B %d, %Y}")
    print(f"Owner: {owner.name} | Pets: {', '.join(p.name for p in owner.pets)}")
    print("-" * 72)
    for item in plan.get_todays_tasks():
        print(
            f"{item.start_time:%H:%M}-{item.end_time:%H:%M}  "
            f"{item.task.title:<18} {item.task.pet_name:<8} {item.reason}"
        )
    if plan.skipped:
        print("\nSkipped:")
        for item in plan.skipped:
            print(f"  {item.task.title:<18} {item.task.pet_name:<8} {item.reason}")
    print("-" * 72)
    print(f"Total scheduled: {plan.total_minutes} of {owner.total_available_minutes()} free minutes")
    if plan.warnings:
        print("\nWarnings:")
        for warning in plan.warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
