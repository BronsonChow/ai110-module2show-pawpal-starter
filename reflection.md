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
