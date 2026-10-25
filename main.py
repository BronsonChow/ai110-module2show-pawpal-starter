"""Demo script: build an owner with two pets and print today's schedule."""

from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TimeWindow


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

    biscuit.schedule_walk(at=time(7, 30), duration=30, priority=Priority.HIGH)
    biscuit.add_task(Task("Breakfast", "feeding", 10, Priority.HIGH, preferred_time=time(7, 0)))
    biscuit.add_task(Task("Evening walk", "walk", 40, Priority.MEDIUM, preferred_time=time(18, 0)))
    mochi.add_task(Task("Thyroid pill", "meds", 5, Priority.HIGH, preferred_time=time(8, 0)))
    mochi.add_task(Task("Feather toy play", "enrichment", 15, Priority.LOW, preferred_time=time(17, 30)))
    mochi.add_task(Task("Brushing", "grooming", 20, Priority.LOW, frequency="weekly"))

    plan = Scheduler(owner).build_daily_plan(date.today())

    print(f"Today's Schedule - {plan.date:%A, %B %d, %Y}")
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


if __name__ == "__main__":
    main()
