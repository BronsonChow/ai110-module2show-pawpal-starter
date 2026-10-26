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
- **Sorting methods return new lists.** `sort_by_priority()` and `apply_preferences()` now return new lists, so building a plan never reorders a pet's own task list. I later merged them into a single `order_for_booking()` method. It sorts once, with priority first and the preferences as tie-breakers, so the order no longer depends on running two sorts in the right sequence.

One thing I deliberately kept is greedy, priority-first scheduling. A long high-priority task can still crowd out several shorter, lower-priority ones. I accepted that because it's simple, predictable and easy to explain to the owner.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

My scheduler considers two kinds of constraints. Hard constraints are never broken. Soft constraints are honored when possible.

**Hard constraints:**

- **Is the task due today?** `is_due()` checks the task's frequency (daily, weekly or once), its due date and whether it's already done. Tasks that aren't due never enter the plan, and missed tasks stay due until they're completed.
- **The owner's free time.** Tasks are booked only inside the owner's `available_windows`, such as 07:00-09:00 and 17:30-19:00. A task that fits in no remaining gap is skipped, and the plan says why.
- **No double-booking.** The scheduler keeps track of booked slots, so two tasks can never be given overlapping times, even for different pets. One person can't walk the dog and give the cat a pill at the same moment.

**Soft constraints, in order of importance:**

1. **Priority** (high, medium, low) decides the booking order, so high-priority tasks get first pick of the free time.
2. **Preferred time.** Each task is placed at its preferred time if that slot is free, or in the nearest free slot if not. Clashing preferred times are reported as warnings.
3. **The owner's category preference** (for example, meds before feeding) breaks ties between tasks of equal priority.
4. **Duration.** Among otherwise equal tasks, shorter ones are booked first.

I ranked them by asking what happens to the pet if each constraint is ignored. Time limits come first because they're physical: the owner simply isn't available outside their free windows, and a schedule that ignores that is useless. Priority comes next because missing a high-priority task like a thyroid pill can harm the pet, while missing playtime only means a less fun day. I treat preferred time as a wish rather than a rule, because a walk at 07:35 instead of 07:30 rarely matters, and making it a hard rule would cause tasks to be skipped for no good reason. Category order and duration are only tie-breakers. They put tasks in a sensible order but should never outrank what the owner said was important. So `order_for_booking()` sorts by priority first and uses the preferences only to break ties.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**The scheduler books tasks greedily, one at a time, and never goes back to rearrange them.** `build_daily_plan()` puts the due tasks in a single order: highest priority first, then preferred time, the owner's category preference and duration as tie-breakers. It then gives each task the free slot closest to its preferred time. Once a task has a slot, it keeps it. When two tasks want the same time, the one booked first wins and the other moves to the nearest free gap. If no gap is long enough, it's skipped.

In the demo, Mochi's dinner and Biscuit's evening walk both want 18:00. Dinner is high priority, so it gets 18:00 and the walk moves to 18:10. Biscuit's ear drops and walk both want 07:30. Both are high priority, but meds ranks above walks in the owner's preferences, so the ear drops keep 07:30 and the walk starts at 07:35. The cost is that the plan isn't always the best possible one. A long high-priority task can take a gap that two shorter, lower-priority tasks would have fit into, and one of them may be skipped even though a different arrangement could fit everything. Conflict detection has the same limit: `detect_conflicts()` only warns about clashing preferred times. It doesn't try other arrangements.

I think this is reasonable for a pet owner's day:

- **Small scale.** There are only a dozen or so tasks and a couple of free windows, so moves are usually a few minutes and skips are rare.
- **Predictable and explainable.** Every decision can be explained in one line, like "high priority, at preferred time" or "nearest free slot to preferred 18:00". An optimizer that reshuffled everything would be much harder for the owner to understand or trust.
- **The important tasks are safe.** Priority always goes first, so the tasks the owner cares about most (meds, feeding) always get their slot. Only less important tasks get moved or dropped.
- **The owner stays informed.** Conflicts are reported as warnings instead of being silently fixed, so the owner can move a task themselves.
- **The alternative is costly.** Finding the best possible arrangement means trying many orderings, and the number grows very fast with the number of tasks. That's a lot of complexity to save a few minutes.

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
