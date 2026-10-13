"""Streamlit UI for the Borderless Meeting Planner.

Pure logic lives in logic.py (see AGENTS.md working rules); this file only
renders widgets and formats display strings. Run with:

    .venv/bin/streamlit run app.py
"""

from datetime import date, datetime, timedelta, timezone

import streamlit as st

from logic import (
    CITIES,
    WEEKDAYS,
    City,
    OverlapWindow,
    format_hours,
    get_city,
    hour_states,
    local_now,
    offset_badge,
    overlap_hours,
    overlap_windows,
)

CELL_STYLES = {
    "outside": "background:#f1f3f5;color:#adb5bd;",
    "working": "background:#dbe4ff;color:#364fc7;",
    "overlap": "background:#2f9e44;color:#ffffff;font-weight:700;",
}


def chip(label: str, style: str) -> str:
    """Small rounded label used for the legend."""
    return (
        '<span style="display:inline-block;padding:2px 12px;border-radius:999px;'
        f'margin-right:6px;font-size:0.8em;{style}">{label}</span>'
    )


def render_legend() -> None:
    html = (
        chip("Working hours", CELL_STYLES["working"])
        + chip("Overlapping hours", CELL_STYLES["overlap"])
        + chip("Outside working hours", CELL_STYLES["outside"])
    )
    st.markdown(html, unsafe_allow_html=True)


def render_hour_row(city: City, states: list[str], view_date: date) -> None:
    """One city's 24 hour cells: gray = outside, blue = working, green = overlap."""
    weekday = WEEKDAYS[view_date.weekday()]
    st.markdown(f"**{city.name}** — {weekday} {view_date.isoformat()} local · green = overlap")
    cells = "".join(
        '<span style="display:inline-block;width:2.6em;text-align:center;margin:2px;'
        f'padding:6px 0;border-radius:6px;font-size:0.8em;{CELL_STYLES[state]}">{hour:02d}</span>'
        for hour, state in enumerate(states)
    )
    st.markdown(f"<div>{cells}</div>", unsafe_allow_html=True)


def format_window(window: OverlapWindow, cities: list[City]) -> str:
    """Readable window: first city's local time, then UTC and the other cities."""
    first = cities[0]
    head = (
        f"{local_now(first, window.start_utc):%H:%M}–"
        f"{local_now(first, window.end_utc):%H:%M} {first.name}"
    )
    rest = [f"{window.start_utc:%H:%M}–{window.end_utc:%H:%M} UTC"]
    rest += [
        f"{local_now(city, window.start_utc):%H:%M}–"
        f"{local_now(city, window.end_utc):%H:%M} {city.name}"
        for city in cities[1:]
    ]
    return f"{head} ({' · '.join(rest)})"


st.set_page_config(page_title="Borderless Meeting Planner", page_icon="🌍", layout="wide")

# --- Sidebar: city picker -----------------------------------------------------
st.sidebar.header("Cities")
selected_names = st.sidebar.multiselect(
    "Add or remove cities",
    options=[city.name for city in CITIES],
    label_visibility="collapsed",
)
st.sidebar.caption(f"{len(selected_names)} of {len(CITIES)} cities selected")

# --- Header --------------------------------------------------------------------
st.title("Borderless Meeting Planner")
st.caption("Find a window where every city is inside 09:00–17:00 local time.")

if not selected_names:
    st.info("Select at least one city in the sidebar to see local clocks and overlapping hours.")
    st.stop()

cities = [get_city(name) for name in selected_names]
now_utc = datetime.now(timezone.utc)
view_date = now_utc.date()
day_start = datetime(view_date.year, view_date.month, view_date.day, tzinfo=timezone.utc)
day_end = day_start + timedelta(days=1)

# --- Metrics -------------------------------------------------------------------
metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("Cities", len(cities))
next_week_hours = overlap_hours(cities, now_utc, now_utc + timedelta(days=7))
metric_col2.metric("Overlapping hours (next 7 days)", format_hours(next_week_hours))

# --- Overlap windows for the view date -----------------------------------------
windows = overlap_windows(cities, day_start, day_end)
st.markdown("**Overlapping windows (view date)**")
if windows:
    for window in windows:
        st.markdown(f"- {format_window(window, cities)}")
elif next_week_hours == 0.0:
    names = ", ".join(city.name for city in cities)
    st.warning(
        f"No overlapping hours at all: {names} are never all within "
        "09:00–17:00 local time (checked over the next 7 days)."
    )
else:
    st.write("No overlap on the view date.")


# --- Local clocks (tick every second) ------------------------------------------
@st.fragment(run_every=timedelta(seconds=1))
def render_local_clocks() -> None:
    st.subheader("Local clocks")
    now = datetime.now(timezone.utc)
    columns = st.columns(len(cities))
    for column, city in zip(columns, cities):
        local = local_now(city, now)
        column.markdown(f"**{city.name}**")
        column.markdown(f"## {local:%H:%M:%S}")
        column.caption(offset_badge(local))


render_local_clocks()

# --- 24-hour local view ---------------------------------------------------------
st.subheader("24-hour local view")
render_legend()
grid = hour_states(cities, view_date)
for city in cities:
    render_hour_row(city, grid[city.name], view_date)
