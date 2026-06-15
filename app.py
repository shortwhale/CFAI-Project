import os
import random
from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st
from supabase import create_client, Client
from postgrest.exceptions import APIError

st.set_page_config(page_title="University Timetable Generator", page_icon="📅", layout="wide")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIME_SLOTS = [
    "09:00 - 10:00",
    "10:00 - 11:00",
    "11:15 - 12:15",
    "12:15 - 01:15",
    "02:00 - 03:00",
    "03:00 - 04:00",
]

DEFAULT_CLASSES = ["CSE-A", "CSE-B", "CSE-C", "IT-A", "ECE-A"]
DEFAULT_SUBJECTS = [
    "Python Programming",
    "Database Management Systems",
    "Artificial Intelligence",
    "Machine Learning",
    "Operating Systems",
    "Computer Networks",
    "Data Structures",
    "Design and Analysis of Algorithms",
    "Software Engineering",
    "Web Technologies",
    "Cloud Computing",
    "Cyber Security",
    "Statistics",
    "Discrete Mathematics",
    "Computer Organization",
]
DEFAULT_TEACHERS = [
    ("Dr Sharma", "Python Programming, Data Structures, Design and Analysis of Algorithms"),
    ("Prof Khan", "Artificial Intelligence, Machine Learning"),
    ("Ms Reddy", "Database Management Systems, Web Technologies"),
    ("Mr Joseph", "Operating Systems, Computer Networks, Computer Organization"),
    ("Dr Mehta", "Cloud Computing, Cyber Security, Software Engineering"),
    ("Ms Iyer", "Statistics, Discrete Mathematics"),
]
DEFAULT_ROOMS = ["Room 101", "Room 102", "Room 103", "Lab 1", "Lab 2"]


def get_secret(name: str, default: str = "") -> str:
    value = ""

    try:
        value = st.secrets[name]
    except Exception:
        value = os.getenv(name, default)

    return str(value).strip()

@st.cache_resource
def get_supabase() -> Client:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Supabase keys are missing. Add SUPABASE_URL and SUPABASE_ANON_KEY.")
        st.stop()
    return create_client(url, key)


def load_table(table_name: str) -> List[Dict]:
    try:
        result = get_supabase().table(table_name).select("*").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Could not load {table_name}: {e}")
        return []


def insert_row(table_name: str, row: Dict):
    return get_supabase().table(table_name).insert(row).execute()


def safe_insert(table_name: str, row: Dict):
    try:
        return insert_row(table_name, row)
    except APIError as e:
        if "duplicate key" not in str(e):
            raise e


def delete_row(table_name: str, row_id: int):
    return get_supabase().table(table_name).delete().eq("id", row_id).execute()


def clear_table(table_name: str):
    get_supabase().table(table_name).delete().neq("id", 0).execute()


def clear_timetable():
    clear_table("timetables")


def save_timetable(entries: List[Dict]):
    if entries:
        get_supabase().table("timetables").insert(entries).execute()


def seed_default_data(reset: bool = False):
    if reset:
        for table in ["timetables", "subjects", "teachers", "rooms", "classes"]:
            clear_table(table)

    for class_name in DEFAULT_CLASSES:
        safe_insert("classes", {"name": class_name})

    for teacher_name, subjects in DEFAULT_TEACHERS:
        safe_insert("teachers", {"name": teacher_name, "subjects": subjects})

    for room_name in DEFAULT_ROOMS:
        safe_insert("rooms", {"name": room_name})


def sync_subjects_for_class(class_id: int, selected_subjects: List[str], weekly_periods: int):
    existing = load_table("subjects")
    existing_names = {
        row["name"] for row in existing if int(row.get("class_id") or 0) == int(class_id)
    }

    for subject_name in selected_subjects:
        if subject_name not in existing_names:
            insert_row(
                "subjects",
                {
                    "name": subject_name,
                    "class_id": int(class_id),
                    "weekly_periods": int(weekly_periods),
                },
            )


def generate_timetable(classes, subjects, teachers, rooms):
    timetable = []
    teacher_busy = set()
    room_busy = set()
    class_busy = set()
    warnings = []

    if not classes or not subjects or not teachers or not rooms:
        return [], ["Need at least one class, subject, teacher, and room."]

    subject_map = {}
    for subject in subjects:
        subject_map.setdefault(subject["class_id"], []).append(subject)

    for class_item in classes:
        class_id = class_item["id"]
        class_name = class_item["name"]
        class_subjects = subject_map.get(class_id, [])

        if not class_subjects:
            continue

        expanded_subjects = []
        for subject in class_subjects:
            for _ in range(int(subject.get("weekly_periods") or 1)):
                expanded_subjects.append(subject)

        random.shuffle(expanded_subjects)

        for subject in expanded_subjects:
            placed = False
            possible_teachers = [
                t for t in teachers
                if subject["name"].lower() in (t.get("subjects") or "").lower()
                or not (t.get("subjects") or "").strip()
            ] or teachers

            for day in random.sample(DAYS, len(DAYS)):
                for slot in random.sample(TIME_SLOTS, len(TIME_SLOTS)):
                    if (class_id, day, slot) in class_busy:
                        continue

                    for teacher in random.sample(possible_teachers, len(possible_teachers)):
                        if (teacher["id"], day, slot) in teacher_busy:
                            continue

                        for room in random.sample(rooms, len(rooms)):
                            if (room["id"], day, slot) in room_busy:
                                continue

                            timetable.append(
                                {
                                    "class_id": class_id,
                                    "class_name": class_name,
                                    "subject_id": subject["id"],
                                    "subject_name": subject["name"],
                                    "teacher_id": teacher["id"],
                                    "teacher_name": teacher["name"],
                                    "room_id": room["id"],
                                    "room_name": room["name"],
                                    "day": day,
                                    "time_slot": slot,
                                    "created_at": datetime.utcnow().isoformat(),
                                }
                            )
                            class_busy.add((class_id, day, slot))
                            teacher_busy.add((teacher["id"], day, slot))
                            room_busy.add((room["id"], day, slot))
                            placed = True
                            break
                        if placed:
                            break
                    if placed:
                        break
                if placed:
                    break

            if not placed:
                warnings.append(f"Could not place {subject['name']} for {class_name}.")

    return timetable, warnings


def render_timetable(timetable_rows):
    if not timetable_rows:
        st.info("No timetable generated yet.")
        return

    df = pd.DataFrame(timetable_rows)
    selected_class = st.selectbox("View timetable for class", sorted(df["class_name"].unique()))
    class_df = df[df["class_name"] == selected_class]

    grid = pd.DataFrame(index=TIME_SLOTS, columns=DAYS)
    for _, row in class_df.iterrows():
        grid.loc[row["time_slot"], row["day"]] = (
            f"{row['subject_name']}\nTeacher: {row['teacher_name']}\nRoom: {row['room_name']}"
        )

    st.dataframe(grid.fillna("-"), use_container_width=True)
    st.download_button(
        "Download Full Timetable CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="university_timetable.csv",
        mime="text/csv",
    )


def show_simple_editor(table_name: str, title: str):
    data = load_table(table_name)
    st.subheader(title)
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.info(f"No {title.lower()} found.")


st.markdown("""
<style>
.main-title {font-size: 42px; font-weight: 800; margin-bottom: 0;}
.subtitle {font-size: 18px; color: #666; margin-top: 4px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">University Timetable Generator</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Python + Supabase app with built-in data and subject selection.</p>', unsafe_allow_html=True)

tabs = st.tabs(["Dashboard", "Select Subjects", "Generate Timetable", "Manage Data", "Setup Help"])

with tabs[0]:
    classes = load_table("classes")
    subjects = load_table("subjects")
    teachers = load_table("teachers")
    rooms = load_table("rooms")
    timetables = load_table("timetables")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Classes", len(classes))
    c2.metric("Selected Subjects", len(subjects))
    c3.metric("Teachers", len(teachers))
    c4.metric("Rooms", len(rooms))
    c5.metric("Timetable Entries", len(timetables))

    if st.button("Load Built-in University Data"):
        seed_default_data(reset=False)
        st.success("Default classes, teachers, and rooms loaded.")
        st.rerun()

    st.divider()
    render_timetable(timetables)

with tabs[1]:
    st.subheader("Select Subjects for a Class")
    st.write("Choose any subjects from the built-in list of 15 subjects. No class ID typing needed.")

    if st.button("Load Default Classes, Teachers, and Rooms", key="seed_subject_tab"):
        seed_default_data(reset=False)
        st.success("Default data loaded.")
        st.rerun()

    classes = load_table("classes")
    if not classes:
        st.warning("Click Load Default Classes, Teachers, and Rooms first.")
    else:
        class_names = [c["name"] for c in classes]
        selected_class_name = st.selectbox("Select Class", class_names)
        selected_class = next(c for c in classes if c["name"] == selected_class_name)

        selected_subjects = st.multiselect(
            "Select subjects for this class",
            DEFAULT_SUBJECTS,
            default=DEFAULT_SUBJECTS[:5],
        )
        weekly_periods = st.slider("Weekly periods per selected subject", 1, 5, 2)

        if st.button("Save Selected Subjects", type="primary"):
            sync_subjects_for_class(selected_class["id"], selected_subjects, weekly_periods)
            st.success(f"Saved {len(selected_subjects)} subjects for {selected_class_name}.")
            st.rerun()

        st.divider()
        current_subjects = [
            s for s in load_table("subjects") if int(s.get("class_id") or 0) == int(selected_class["id"])
        ]
        st.write(f"Current subjects for {selected_class_name}")
        if current_subjects:
            st.dataframe(pd.DataFrame(current_subjects), use_container_width=True, hide_index=True)
        else:
            st.info("No subjects selected for this class yet.")

with tabs[2]:
    st.subheader("Generate New Timetable")
    st.warning("This replaces the old generated timetable.")

    if st.button("Generate Timetable", type="primary"):
        classes = load_table("classes")
        subjects = load_table("subjects")
        teachers = load_table("teachers")
        rooms = load_table("rooms")
        timetable, warnings = generate_timetable(classes, subjects, teachers, rooms)
        clear_timetable()
        save_timetable(timetable)
        st.success(f"Generated {len(timetable)} timetable entries.")
        for warning in warnings:
            st.warning(warning)
        st.rerun()

with tabs[3]:
    section = st.radio("Choose section", ["Classes", "Selected Subjects", "Teachers", "Rooms"], horizontal=True)
    if section == "Classes":
        st.subheader("Classes")
        with st.form("add_class", clear_on_submit=True):
            name = st.text_input("Class Name")
            if st.form_submit_button("Add Class") and name.strip():
                safe_insert("classes", {"name": name.strip()})
                st.success("Class added.")
                st.rerun()
        show_simple_editor("classes", "Existing Classes")
    elif section == "Selected Subjects":
        show_simple_editor("subjects", "Selected Subjects")
    elif section == "Teachers":
        show_simple_editor("teachers", "Teachers")
    elif section == "Rooms":
        show_simple_editor("rooms", "Rooms")

    st.divider()
    st.subheader("Danger Zone")
    if st.button("Reset and Load Fresh Default Data"):
        seed_default_data(reset=True)
        st.success("Reset complete. Now go to Select Subjects.")
        st.rerun()

with tabs[4]:
    st.subheader("Run Locally")
    st.code("""
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
""")
    st.subheader("Supabase Setup")
    st.code("""
1. Run supabase_schema.sql in Supabase SQL Editor.
2. Add SUPABASE_URL and SUPABASE_ANON_KEY in .streamlit/secrets.toml.
3. Open the app and click Load Built-in University Data.
4. Go to Select Subjects and choose subjects for each class.
5. Generate Timetable.
""")
