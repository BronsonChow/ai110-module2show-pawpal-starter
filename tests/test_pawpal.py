from datetime import date

from pawpal_system import Pet, Task


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
