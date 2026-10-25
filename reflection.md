# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My initial design is built around three core actions: adding a pet, scheduling a walk, and seeing today's tasks. It uses five classes:

- **Owner** – Holds the owner's pets and their constraints: how many minutes they have available and their preferences (for example, morning walks). Handles *adding a pet*.
- **Pet** – Stores basic pet info and the pet's list of care tasks. Handles *scheduling a walk* (or any other task) by creating a Task and attaching it to the pet.
- **Task** – A single care item such as a walk, feeding, meds, enrichment, or grooming. It stores the category, duration, priority, preferred time, and whether it is complete.
- **Scheduler** – Applies the constraints. It collects every task from the owner's pets, sorts them by priority, applies owner preferences, and drops tasks that don't fit in the available time.
- **DailyPlan** – The Scheduler's output and how the user *sees today's tasks*. It lists the scheduled and skipped tasks and explains why the plan was chosen.

An Owner has many Pets and a Pet has many Tasks. The Scheduler reads constraints from the Owner and creates a DailyPlan. I kept the scheduling logic in one class, the Scheduler, so Task only stores data and the plan is easy to explain and test.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. When I reviewed the skeleton, I found three relationships my initial design was missing, and I changed the design to fill them in:

- **Tasks now know which pet they belong to.** The Scheduler merges every pet's tasks into one list, which lost track of whose task was whose. A plan saying "Walk – 30 min" is useless with two dogs. I added a `pet_name` field to `Task`, which `Pet.add_task()` fills in.
- **The plan now stores times and reasons.** `DailyPlan` used to hold a plain list of tasks, so it had nowhere to record when each task happens or why it was chosen or skipped, and `explain()` had nothing to work with. I added a small `ScheduledItem` class (task, start time, reason). `DailyPlan` now holds lists of these instead of raw tasks.
- **Tasks now repeat and have due dates.** Nothing in the original design said whether a task was due *today*, and the `completed` flag never reset, so a walk done today would still count as done tomorrow. I replaced `completed` with `frequency`, `due_date` and `last_completed`, plus an `is_due(day)` method. `Scheduler.build_daily_plan()` now takes a date, so it only plans tasks due that day.

I also found several spots where the scheduling logic would have caused problems, and I changed the design to avoid them:

- **Priority is now an enum instead of free text.** With `priority` as a string, a typo like `"hgih"` would quietly sort wrong. I added a `Priority` enum (LOW = 1, MEDIUM = 2, HIGH = 3), so invalid values fail immediately and the enum value doubles as the sort score.
- **Times now use one format.** `preferred_time` could be `"08:00"` or `"morning"`, and those can't be compared or sorted. `preferred_time` and `ScheduledItem.start_time` now both use Python's `datetime.time`.
- **The order of the scheduling steps is now fixed.** It wasn't clear whether preferences ran before or after the priority sort, so preferences could undo it. `build_daily_plan()` now always runs in this order: keep tasks that are due, sort by priority, then book each task into a free slot. Preferences only break ties *within* a priority level, so they can never outrank priority or bring back a task that was skipped for lack of time.
- **Free time is now a list of time windows instead of one number.** A single `available_minutes` value couldn't say "free 7–9am and 6–8pm". I added a `TimeWindow` class, and `Owner` now has `available_windows`, so the scheduler can give tasks real start times. `fits_in_time()` checks whether any free gap across the windows is long enough for a task.
- **Preferred times are now real start times.** My first implementation packed tasks back to back from the start of each window, so a walk preferred at 07:15 could end up at 07:00. The scheduler now keeps track of booked slots and uses `find_slot()` to place each task exactly at its preferred time if that slot is free, or in the nearest free gap if not. Tasks without a preferred time take the earliest free gap.
- **Sorting methods return new lists.** `sort_by_priority()` and `apply_preferences()` now return new lists, so building a plan never reorders a pet's own task list.

One thing I deliberately kept is greedy, priority-first scheduling. A long high-priority task can still crowd out several shorter, lower-priority ones. I accepted that because it's simple, predictable and easy to explain to the owner.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
