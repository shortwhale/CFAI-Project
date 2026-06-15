# University Timetable Generator

Python-only Streamlit + Supabase timetable generator.

## What is new

- Built-in default classes
- Built-in 15 subjects
- Built-in teachers and rooms
- No need to type class IDs for subjects
- User selects class from dropdown
- User selects subjects from multiselect
- Timetable is generated and saved in Supabase

## Run locally

```bash
cd university_timetable_generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Supabase setup

1. Create Supabase project.
2. Open SQL Editor.
3. Run `supabase_schema.sql`.
4. Add `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-public-key"
```

## App steps

1. Open the app.
2. Click **Load Built-in University Data**.
3. Go to **Select Subjects**.
4. Select class.
5. Select subjects from the 15 subjects list.
6. Save selected subjects.
7. Go to **Generate Timetable**.
8. Click **Generate Timetable**.
