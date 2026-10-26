from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TimeWindow


def test_mark_complete_changes_task_status():
    task = Task("Breakfast", "feeding", 10)
    today = date(2026, 10, 25)
    assert not task.is_completed_on(today)
    assert task.is_due(today)

    task.mark_complete(today)

    assert task.is_completed_on(today)
    assert not task.is_due(today)


def test_add_task_increases_pet_task_count():
    pet = Pet("Biscuit", "dog")
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task("Walk", "walk", 30))

    assert len(pet.get_tasks()) == 1


def make_scheduler():
    owner = Owner("Sam", available_windows=[TimeWindow(time(7, 0), time(9, 0))])
    biscuit, mochi = Pet("Biscuit", "dog"), Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return Scheduler(owner), biscuit, mochi


def test_sort_by_time_orders_by_preferred_time_untimed_last():
    scheduler, biscuit, _ = make_scheduler()
    late = Task("Late", "walk", 10, preferred_time=time(18, 0))
    untimed = Task("Whenever", "other", 10)
    early = Task("Early", "feeding", 10, preferred_time=time(7, 0))

    result = scheduler.sort_by_time([late, untimed, early])

    assert [t.title for t in result] == ["Early", "Late", "Whenever"]


def test_filter_tasks_by_pet_and_status():
    scheduler, biscuit, mochi = make_scheduler()
    today = date(2026, 10, 25)
    walk = Task("Walk", "walk", 30)
    breakfast = Task("Breakfast", "feeding", 10)
    pill = Task("Pill", "meds", 5)
    biscuit.add_task(walk)
    biscuit.add_task(breakfast)
    mochi.add_task(pill)
    walk.mark_complete(today)

    assert scheduler.filter_tasks(pet_name="Mochi") == [pill]
    assert scheduler.filter_tasks(completed=True, day=today) == [walk]
    assert scheduler.filter_tasks(pet_name="Biscuit", completed=False, day=today) == [breakfast]


def test_completing_daily_task_creates_next_day_occurrence():
    pet = Pet("Biscuit", "dog")
    walk = Task("Walk", "walk", 30, frequency="daily")
    pet.add_task(walk)
    today = date(2026, 10, 25)

    next_walk = pet.complete_task(walk, today)

    assert next_walk.due_date == today + timedelta(days=1)
    assert next_walk.pet_name == "Biscuit"
    assert len(pet.get_tasks()) == 2
    assert not next_walk.is_due(today)
    assert next_walk.is_due(today + timedelta(days=1))
    assert not walk.is_due(today + timedelta(days=1))  # old instance never comes back


def test_completing_weekly_task_skips_a_week():
    pet = Pet("Mochi", "cat")
    brushing = Task("Brushing", "grooming", 20, frequency="weekly")
    pet.add_task(brushing)
    today = date(2026, 10, 25)

    next_brushing = pet.complete_task(brushing, today)

    assert next_brushing.due_date == today + timedelta(weeks=1)
    assert not next_brushing.is_due(today + timedelta(days=6))
    assert next_brushing.is_due(today + timedelta(days=7))


def test_completing_once_task_does_not_recur():
    pet = Pet("Mochi", "cat")
    vet = Task("Vet visit", "vet", 60, frequency="once")
    pet.add_task(vet)

    assert pet.complete_task(vet, date(2026, 10, 25)) is None
    assert len(pet.get_tasks()) == 1


def test_missed_daily_task_stays_due():
    walk = Task("Walk", "walk", 30, due_date=date(2026, 10, 24))
    assert walk.is_due(date(2026, 10, 25))


def test_detect_conflicts_flags_overlapping_preferred_times():
    scheduler, biscuit, mochi = make_scheduler()
    biscuit.add_task(Task("Walk", "walk", 30, preferred_time=time(7, 30)))
    mochi.add_task(Task("Pill", "meds", 5, preferred_time=time(7, 45)))
    biscuit.add_task(Task("Breakfast", "feeding", 10, preferred_time=time(8, 0)))  # starts as walk ends

    warnings = scheduler.detect_conflicts(date(2026, 10, 25))

    assert len(warnings) == 1
    assert "Walk" in warnings[0] and "Pill" in warnings[0]


def test_conflicts_become_plan_warnings_without_double_booking():
    scheduler, biscuit, mochi = make_scheduler()
    biscuit.add_task(Task("Walk", "walk", 30, Priority.HIGH, preferred_time=time(7, 30)))
    mochi.add_task(Task("Play", "enrichment", 15, Priority.LOW, preferred_time=time(7, 30)))

    plan = scheduler.build_daily_plan(date(2026, 10, 25))

    assert len(plan.warnings) == 1
    walk, play = sorted(plan.scheduled, key=lambda item: item.task.priority_score(), reverse=True)
    assert walk.start_time == time(7, 30)
    assert play.start_time != time(7, 30)
    assert "Warnings:" in plan.explain()


def test_scheduler_mark_task_complete_adds_next_occurrence_to_pet():
    scheduler, biscuit, mochi = make_scheduler()
    walk = Task("Walk", "walk", 30, frequency="daily", preferred_time=time(7, 30))
    brushing = Task("Brushing", "grooming", 20, frequency="weekly")
    biscuit.add_task(walk)
    mochi.add_task(brushing)
    today = date(2026, 10, 25)

    next_walk = scheduler.mark_task_complete(walk, today)
    next_brushing = scheduler.mark_task_complete(brushing, today)

    assert next_walk in biscuit.get_tasks() and next_walk.due_date == today + timedelta(days=1)
    assert next_walk.preferred_time == time(7, 30)  # details carry over
    assert next_brushing in mochi.get_tasks() and next_brushing.due_date == today + timedelta(weeks=1)
    assert walk not in scheduler.get_due_tasks(today + timedelta(days=1))
    assert next_walk in scheduler.get_due_tasks(today + timedelta(days=1))


def test_scheduler_mark_task_complete_rejects_unattached_task():
    scheduler, _, _ = make_scheduler()
    with pytest.raises(ValueError):
        scheduler.mark_task_complete(Task("Stray", "other", 5), date(2026, 10, 25))


def test_detect_conflicts_same_pet_same_time():
    scheduler, biscuit, _ = make_scheduler()
    biscuit.add_task(Task("Walk", "walk", 30, preferred_time=time(7, 30)))
    biscuit.add_task(Task("Ear drops", "meds", 5, preferred_time=time(7, 30)))

    warnings = scheduler.detect_conflicts(date(2026, 10, 25))

    assert warnings == ["Conflict: Walk and Ear drops are both at 07:30 - both for Biscuit"]


def test_detect_conflicts_none_when_tasks_do_not_overlap():
    scheduler, biscuit, mochi = make_scheduler()
    biscuit.add_task(Task("Walk", "walk", 30, preferred_time=time(7, 0)))
    mochi.add_task(Task("Pill", "meds", 5, preferred_time=time(7, 30)))  # starts as walk ends
    mochi.add_task(Task("Brushing", "grooming", 20))  # no preferred time, can't clash

    assert scheduler.detect_conflicts(date(2026, 10, 25)) == []
