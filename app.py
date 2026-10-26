from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task, TimeWindow

CATEGORIES = ["walk", "feeding", "meds", "enrichment", "grooming", "vet", "other"]

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan your pets' care around your free time, task priority, and your preferences.")

# --- Session "vault": create the Owner once, reuse it on every rerun ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name="Jordan",
        available_windows=[
            TimeWindow(time(7, 0), time(9, 0)),
            TimeWindow(time(17, 30), time(19, 0)),
        ],
    )

owner: Owner = st.session_state.owner

with st.sidebar:
    st.header("Session")
    if st.button("Reset everything"):
        del st.session_state["owner"]
        st.rerun()

# --- Owner ---
st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)

st.markdown("**Free time today**")
if owner.available_windows:
    for i, window in enumerate(sorted(owner.available_windows, key=lambda w: w.start)):
        col_label, col_remove = st.columns([4, 1])
        col_label.write(f"{window}  ({window.minutes()} min)")
        if col_remove.button("Remove", key=f"remove_window_{i}"):
            owner.available_windows.remove(window)
            st.rerun()
else:
    st.info("No free time set. Add a window below.")

col1, col2, col3 = st.columns([2, 2, 1])
window_start = col1.time_input("Start", value=time(12, 0), step=900)
window_end = col2.time_input("End", value=time(13, 0), step=900)
col3.write("")
if col3.button("Add window"):
    try:
        owner.available_windows.append(TimeWindow(window_start, window_end))
        st.rerun()
    except ValueError as err:
        st.error(str(err))

category_order = st.multiselect(
    "Category preference (tie-breaker when priorities are equal, first = most preferred)",
    CATEGORIES,
    default=owner.preferences.get("category_order", []),
)
owner.preferences["category_order"] = category_order

st.divider()

# --- Pets ---
st.subheader("Pets")
col1, col2, col3 = st.columns([2, 2, 1])
pet_name = col1.text_input("Pet name", value="Mochi")
species = col2.selectbox("Species", ["dog", "cat", "other"])
age = col3.number_input("Age", min_value=0, max_value=40, value=3)

if st.button("Add pet"):
    try:
        owner.add_pet(Pet(pet_name.strip(), species, int(age)))
        st.success(f"Added {pet_name}.")
    except ValueError as err:
        st.error(str(err))

if owner.pets:
    st.table(
        [{"Name": p.name, "Species": p.species, "Age": p.age, "Tasks": len(p.tasks)} for p in owner.pets]
    )
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Tasks ---
st.subheader("Tasks")
if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    col1, col2 = st.columns(2)
    pet_choice = col1.selectbox("For pet", [p.name for p in owner.pets])
    task_title = col2.text_input("Task title", value="Morning walk")

    col1, col2, col3 = st.columns(3)
    category = col1.selectbox("Category", CATEGORIES)
    duration = col2.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    priority_name = col3.selectbox("Priority", ["LOW", "MEDIUM", "HIGH"], index=2)

    col1, col2, col3 = st.columns(3)
    frequency = col1.selectbox("Frequency", ["daily", "weekly", "once"])
    has_preferred = col2.checkbox("Preferred time?")
    preferred = col3.time_input("At", value=time(8, 0), step=900, disabled=not has_preferred)

    if st.button("Add task"):
        try:
            owner.get_pet(pet_choice).add_task(
                Task(
                    title=task_title,
                    category=category,
                    duration_minutes=int(duration),
                    priority=Priority[priority_name],
                    preferred_time=preferred if has_preferred else None,
                    frequency=frequency,
                    due_date=date.today() if frequency == "once" else None,
                )
            )
            st.success(f"Added '{task_title}' for {pet_choice}.")
        except ValueError as err:
            st.error(str(err))

    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.table(
            [
                {
                    "Pet": t.pet_name,
                    "Task": t.title,
                    "Category": t.category,
                    "Minutes": t.duration_minutes,
                    "Priority": t.priority.name.lower(),
                    "Preferred": f"{t.preferred_time:%H:%M}" if t.preferred_time else "-",
                    "Frequency": t.frequency,
                }
                for t in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# --- Schedule ---
st.subheader("Today's Schedule")
plan_day = st.date_input("Plan for", value=date.today())

if st.button("Generate schedule", type="primary"):
    plan = Scheduler(owner).build_daily_plan(plan_day)

    if plan.scheduled:
        st.table(
            [
                {
                    "Time": f"{item.start_time:%H:%M}-{item.end_time:%H:%M}",
                    "Task": item.task.title,
                    "Pet": item.task.pet_name,
                    "Why": item.reason,
                }
                for item in plan.get_todays_tasks()
            ]
        )
        st.caption(
            f"{plan.total_minutes} of {owner.total_available_minutes()} free minutes scheduled."
        )
    else:
        st.info("Nothing scheduled. Add pets, tasks, and free time first.")

    for item in plan.skipped:
        st.warning(f"Skipped **{item.task.title}** ({item.task.pet_name}): {item.reason}")

    with st.expander("Plan explanation"):
        st.text(plan.explain())
