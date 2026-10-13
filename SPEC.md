# SPEC — Borderless Meeting Planner

Find a window where every city is inside 09:00–17:00 local time.

Stack: Python 3.13, Streamlit (`app.py`), pytest (`test_logic.py`). All pure logic lives in `logic.py` (see AGENTS.md working rules). Time zones via stdlib `zoneinfo`. Only extra libraries allowed: `streamlit`, `pytest`.

## Features

1. **City picker (sidebar)** — chip-style multiselect over the built-in 36-city catalog (`CITIES`), caption `N of 36 cities selected`. Default: nothing selected; main area shows a "select at least one city" prompt.
2. **Metrics row**
   - `Cities` — number of selected cities.
   - `Overlapping hours (next 7 days)` — total hours in `[now, now + 7 days)` when **every** selected city is within working hours, formatted `X.X h`.
3. **Overlap window line** — for the view date, each window where all cities are working, shown readable, e.g.
   `09:00–10:00 London (08:00–09:00 UTC · 16:00–17:00 Bali)`; `No overlap on the view date` when that date has none. If the 7-day overlap is **zero at all** (e.g. Tokyo + London), show a warning naming the cities instead.
4. **Local clocks** — one per selected city: `HH:MM:SS` plus badge `↑/↓ · weekday · UTC±X` (↑ ahead of UTC, ↓ behind, `=` exactly UTC), refreshed every second.
5. **24-hour local view** — legend: Working hours (blue), Overlapping hours (green), Outside working hours (gray). One row per city: `City — Www YYYY-MM-DD local · green = overlap`, cells `00`–`23`.
6. **Weekends** — Saturday and Sunday are never working hours. A weekend view date renders an all-gray grid and contributes 0 overlapping hours.

### Definitions

- **Working hours**: Mon–Fri, `09:00 <= local time < 17:00`.
- **Overlap**: an instant where every selected city is within its own working hours. With a single city this is vacuously true, so its working hours show green and the metric equals its working hours.
- **View date**: today's date (UTC). Each row renders that date's hours 00–23 in the city's local time.
- **Cell state**: a cell is *working* if the entire local hour `[h:00, h+1:00)` lies inside working hours for that city; *overlap* (green) if the same absolute hour lies inside working hours for **every** selected city; otherwise *outside*. The metric uses exact window durations, so it can differ from the green-cell count (e.g. Delhi's half-hour offset: 3.5 h vs 3 whole green cells).

## Data structure

```python
@dataclass(frozen=True)
class City:
    name: str   # unique display name, e.g. "London"
    tz: str     # IANA zone for zoneinfo, e.g. "Europe/London"

CITIES: tuple[City, ...]      # 36-entry catalog, module-level constant in logic.py

HourState = "outside" | "working" | "overlap"   # one per grid cell

@dataclass(frozen=True)
class OverlapWindow:
    start_utc: datetime  # inclusive
    end_utc: datetime    # exclusive
```

Selection = list of city names in display order (Streamlit multiselect values).

### Public API (`logic.py`)

| Function | Purpose |
|---|---|
| `get_city(name) -> City` | catalog lookup; raises `KeyError` if unknown |
| `local_now(city, now_utc) -> datetime` | aware local time for an aware UTC instant |
| `offset_badge(local_dt) -> str` | e.g. `"↑ Monday · UTC+1"` (fixed English weekday, no locale) |
| `is_working(local_dt) -> bool` | Mon–Fri and `09:00 <= t < 17:00` |
| `hour_states(cities, date) -> dict[str, list[HourState]]` | 24 cells per city, insertion order |
| `overlap_windows(cities, start_utc, end_utc) -> list[OverlapWindow]` | contiguous all-working UTC intervals |
| `overlap_hours(cities, start_utc, end_utc) -> float` | sum of window durations, in hours |
| `format_hours(h) -> str` | `"5.0 h"` |

All functions are pure: no clock reads, no I/O. Callers pass `now` explicitly; `app.py` is the only place that reads the current time.

## Acceptance criteria (example test cases → `test_logic.py`)

| # | Test | Given / When | Expected |
|---|---|---|---|
| 1 | `test_is_working_boundaries` | Tue 2026-10-13 local times; Sat 2026-10-17 noon | 08:59 ✗, 09:00 ✓, 16:59 ✓, 17:00 ✗; Saturday ✗ |
| 2 | `test_local_clocks_match_mockup` | `now = 2026-10-12T15:22:21Z`, London / Bali | `16:22:21` + `↑ Monday · UTC+1`; `23:22:21` + `↑ Monday · UTC+8` |
| 3 | `test_catalog_has_36_valid_cities` | `CITIES` | exactly 36, unique names, every `tz` resolves via `ZoneInfo` |
| 4 | `test_get_city` | `"London"`, `"Atlantis"` | returns city; `KeyError` for unknown |
| 5 | `test_grid_london_bali_matches_mockup` | `hour_states([London, Bali], 2026-10-13)` | London: cell 09 green, 10–16 blue, rest gray; Bali: cell 16 green, 09–15 blue, rest gray |
| 6 | `test_overlap_london_bali_single_day` | `[2026-10-13T00:00Z, 2026-10-14T00:00Z)` | one window `08:00–09:00 UTC`, `1.0 h` (= London 09–10, Bali 16–17 local) |
| 7 | `test_overlap_next_7_days_matches_mockup_metric` | London+Bali, `[2026-10-13, 2026-10-20)` UTC | `5.0 h` (5 weekdays × 1 h — weekends excluded), renders `5.0 h` |
| 8 | `test_no_overlap_san_francisco_tokyo` | both, 7-day range | `[]` windows, `0.0 h`; grid still has blue working cells, no green |
| 9 | `test_same_offset_full_day_london_dublin` | both, one weekday | `8.0 h`; cells 09–16 green, 08 and 17 gray |
| 10 | `test_half_hour_offset_delhi` | London+Delhi, one weekday | window `08:00–11:30 UTC`, `3.5 h`, renders `3.5 h` |
| 11 | `test_dst_shift_london_new_york` | London+NY: 2026-10-20 / 2026-10-27 / 2026-11-03 | `13:00–16:00 UTC` (3.0 h, both on DST); `13:00–17:00 UTC` (4.0 h, London off DST, NY still EDT); `14:00–17:00 UTC` (3.0 h, both off DST) |
| 12 | `test_empty_selection` | no cities | no windows, `0.0 h`, empty grid, no crash |
| 13 | `test_single_city_vacuous_overlap` | London alone, one weekday | `8.0 h`; cells 09–16 green |
| 14 | `test_weekend_grid_all_outside` | London+Bali, Sat 2026-10-17 | all cells `outside`, `0.0 h` that day |
| 15 | `test_warns_when_no_overlap_at_all` (in `test_app.py`, AppTest) | Tokyo+London selected | app shows a warning naming both cities (7-day overlap is 0) |
| 16 | `test_no_warning_when_overlap_exists` (in `test_app.py`, AppTest) | London+Bali selected | no warning shown |

## Constraints / non-goals

- Follow AGENTS.md working rules: plan first; pure logic in `logic.py`, UI in `app.py`, every `logic.py` function tested in `test_logic.py`; `pytest` green after every change.
- `zoneinfo` for time zones; only `streamlit` and `pytest` beyond the stdlib (no pandas/numpy).
- Non-goals: no persistence, no network, no auth, no calendar export, no extra dependencies.
