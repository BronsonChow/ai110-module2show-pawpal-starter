# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
Today's Schedule - Sunday, October 25, 2026
Owner: Sam | Pets: Biscuit, Mochi
------------------------------------------------------------------------
07:00-07:10  Breakfast          Biscuit  high priority, at preferred time
07:10-07:30  Brushing           Mochi    low priority, earliest free slot
07:30-08:00  Walk Biscuit       Biscuit  high priority, at preferred time
08:00-08:05  Thyroid pill       Mochi    high priority, at preferred time
17:30-17:45  Feather toy play   Mochi    low priority, at preferred time
18:00-18:40  Evening walk       Biscuit  medium priority, at preferred time
------------------------------------------------------------------------
Total scheduled: 120 of 210 free minutes
```

## 📐 Smarter Scheduling

All scheduling logic is in [`pawpal_system.py`](pawpal_system.py). Run `python main.py` to see every feature below in the terminal; the example output in this section comes from that script.

| Feature | Method(s) | In one line |
|---------|-----------|-------------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.order_for_booking()` | List tasks by time; book them by priority |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.get_due_tasks()` | By pet, by done/pending, or both |
| Conflict detection | `Scheduler.detect_conflicts()`, `DailyPlan.warnings` | Warn about clashing preferred times, never crash |
| Recurring tasks | `Scheduler.mark_task_complete()`, `Pet.complete_task()`, `Task.mark_complete()` | Completing a daily/weekly task creates the next one |

### Sorting

- **`Scheduler.sort_by_time(tasks)`** returns a new list ordered by each task's `preferred_time`, earliest first. Tasks without a preferred time go last. The sort key is `(preferred_time is None, preferred_time)`. Preferred times are stored as `datetime.time` rather than strings, so they compare correctly with no parsing.
- **`Scheduler.order_for_booking(tasks)`** sets the order in which `build_daily_plan()` books tasks. It's one sort with the key `(priority, has preferred time, preferred time, category preference, duration)`. Priority always comes first, and the owner's preferences only break ties within a priority level.

Neither method changes a pet's own task list; both return new lists.

```
Sorted by time (sort_by_time):
  07:00     Breakfast          Biscuit  pending
  07:30     Walk Biscuit       Biscuit  pending
  07:30     Ear drops          Biscuit  pending
  07:45     Litter box         Mochi    pending
  ...
  18:00     Dinner             Mochi    pending
  any time  Brushing           Mochi    pending
```

### Filtering

- **`Scheduler.filter_tasks(pet_name=None, completed=None, day=None)`** returns the owner's tasks that match every filter given:
  - `pet_name="Mochi"`: only that pet's tasks.
  - `completed=True`: tasks marked done on `day`.
  - `completed=False`: tasks still pending on `day`.
  - Filters combine. For example, `filter_tasks(pet_name="Mochi", completed=False)` gives Mochi's to-do list. `day` defaults to today.
- **`Scheduler.get_due_tasks(day)`** returns only the tasks due on `day`. `build_daily_plan()` uses it, so completed tasks and tasks not due yet never enter the plan.
- Tasks that don't fit in any free gap are skipped and listed in `DailyPlan.skipped`, with the reason ("no free gap of 40 min left").

```
Mochi's pending tasks (pet_name='Mochi', completed=False):
  07:45     Litter box         Mochi    pending
  17:30     Feather toy play   Mochi    pending
  18:00     Dinner             Mochi    pending
  any time  Brushing           Mochi    pending
```

### Conflict detection

- **`Scheduler.detect_conflicts(day)`** returns a list of warning messages. It never raises an exception. It flags any two due tasks whose preferred time slots (preferred time + duration) overlap, for the same pet or for different pets.
- **How it works:** it sorts the timed tasks by start time, then compares each task only with the tasks after it, stopping at the first one that starts after it ends. Since the list is sorted, no later task can overlap.
- **Wording:** tasks that start at exactly the same time get a "both at HH:MM" message. Partial overlaps get an "overlaps" message.
- **In the plan:** `build_daily_plan()` saves the warnings in **`DailyPlan.warnings`**, which `explain()`, `main.py` and the Streamlit app all show. The plan is still built, and the booking step never double-books. The higher-priority task keeps its slot, and the other moves to the nearest free gap.

```
Conflict check (detect_conflicts):
  WARNING Conflict: Walk Biscuit and Ear drops are both at 07:30 - both for Biscuit
  WARNING Conflict: Walk Biscuit (07:30, 30 min) overlaps Litter box (07:45) - Biscuit and Mochi
  WARNING Conflict: Evening walk and Dinner are both at 18:00 - Biscuit and Mochi
```

### Recurring tasks

- **`Scheduler.mark_task_complete(task, day)`** is the single call for completing a task. It finds the task's pet, marks the task done and adds the next copy to that pet. A task that belongs to no pet raises a `ValueError`.
- **`Pet.complete_task(task, day)`** marks one of the pet's tasks done and adds the next copy to the pet's task list.
- **`Task.mark_complete(day)`** records the completion and returns the next copy. It uses `dataclasses.replace`, so title, duration, priority, preferred time and pet carry over. The due date is calculated with `timedelta`:
  - `"daily"`: `day + timedelta(days=1)`
  - `"weekly"`: `day + timedelta(weeks=1)`
  - `"once"`: no next copy; returns `None`

  Because this is date arithmetic, month ends, year ends and leap days roll over correctly.
- **`Task.is_due(day)`** follows one rule for every frequency: a task is due from its due date until it's marked complete. The completed copy is never due again, and the new copy carries the repeat forward. A missed task stays due until it's done, rather than quietly resetting the next day.

```
Completed Breakfast and Thyroid pill; next breakfast due Monday 26 Oct
Biscuit's tasks (pet_name='Biscuit'):
  07:00     Breakfast          Biscuit  done
  07:00     Breakfast          Biscuit  next due Mon 26 Oct
```

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
