"""Pure logic for the Borderless Meeting Planner.

UI lives in app.py; tests live in test_logic.py (see AGENTS.md working rules).
All functions are pure: no clock reads, no I/O — callers pass `now` explicitly.
Time zones come from the stdlib `zoneinfo` module only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

HourState = Literal["outside", "working", "overlap"]

UTC = timezone.utc
HOUR = timedelta(hours=1)
WORK_START = time(9, 0)
WORK_END = time(17, 0)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class City:
    name: str  # unique display name
    tz: str  # IANA zone name for zoneinfo


CITIES: tuple[City, ...] = (
    City("London", "Europe/London"),
    City("Bali", "Asia/Makassar"),  # WITA, UTC+8; Asia/Denpasar link missing from tzdata
    City("New York", "America/New_York"),
    City("San Francisco", "America/Los_Angeles"),
    City("Tokyo", "Asia/Tokyo"),
    City("Delhi", "Asia/Kolkata"),
    City("Sydney", "Australia/Sydney"),
    City("Reykjavik", "Atlantic/Reykjavik"),
    City("Paris", "Europe/Paris"),
    City("Berlin", "Europe/Berlin"),
    City("Madrid", "Europe/Madrid"),
    City("Rome", "Europe/Rome"),
    City("Amsterdam", "Europe/Amsterdam"),
    City("Zurich", "Europe/Zurich"),
    City("Stockholm", "Europe/Stockholm"),
    City("Moscow", "Europe/Moscow"),
    City("Dubai", "Asia/Dubai"),
    City("Mumbai", "Asia/Kolkata"),
    City("Singapore", "Asia/Singapore"),
    City("Hong Kong", "Asia/Hong_Kong"),
    City("Shanghai", "Asia/Shanghai"),
    City("Seoul", "Asia/Seoul"),
    City("Bangkok", "Asia/Bangkok"),
    City("Jakarta", "Asia/Jakarta"),
    City("Manila", "Asia/Manila"),
    City("Karachi", "Asia/Karachi"),
    City("Dhaka", "Asia/Dhaka"),
    City("Cairo", "Africa/Cairo"),
    City("Lagos", "Africa/Lagos"),
    City("Nairobi", "Africa/Nairobi"),
    City("Johannesburg", "Africa/Johannesburg"),
    City("Sao Paulo", "America/Sao_Paulo"),
    City("Buenos Aires", "America/Argentina/Buenos_Aires"),
    City("Mexico City", "America/Mexico_City"),
    City("Toronto", "America/Toronto"),
    City("Dublin", "Europe/Dublin"),
)

_CITIES_BY_NAME: dict[str, City] = {city.name: city for city in CITIES}


@dataclass(frozen=True)
class OverlapWindow:
    start_utc: datetime  # inclusive
    end_utc: datetime  # exclusive


def get_city(name: str) -> City:
    """Look up a catalog city by display name; raises KeyError if unknown."""
    return _CITIES_BY_NAME[name]


def local_now(city: City, now_utc: datetime) -> datetime:
    """Convert an aware UTC instant to the city's aware local time."""
    return now_utc.astimezone(ZoneInfo(city.tz))


def offset_badge(local_dt: datetime) -> str:
    """Badge like '↑ Monday · UTC+1'. ↑ ahead of UTC, ↓ behind, '=' exactly UTC."""
    offset = local_dt.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    label = f"UTC{sign}{hours}" if minutes == 0 else f"UTC{sign}{hours}:{minutes:02d}"
    arrow = "↑" if total_minutes > 0 else "↓" if total_minutes < 0 else "="
    weekday = WEEKDAYS[local_dt.weekday()]
    return f"{arrow} {weekday} · {label}"


def is_working(local_dt: datetime) -> bool:
    """True iff Mon–Fri and 09:00 <= local time < 17:00."""
    if local_dt.weekday() >= 5:
        return False
    t = local_dt.time()
    return WORK_START <= t < WORK_END


def _hour_is_within_working(start_utc: datetime, city: City) -> bool:
    """True iff the absolute hour starting at `start_utc` lies entirely inside
    the city's working hours (full-hour containment rule from SPEC.md)."""
    tz = ZoneInfo(city.tz)
    local_start = start_utc.astimezone(tz)
    if not is_working(local_start):
        return False
    local_end = (start_utc + HOUR).astimezone(tz)
    return local_end.time() <= WORK_END and local_end.date() == local_start.date()


def hour_states(cities: Sequence[City], view_date: date) -> dict[str, list[HourState]]:
    """24 cell states per city for the given date in each city's local time."""
    result: dict[str, list[HourState]] = {}
    for city in cities:
        tz = ZoneInfo(city.tz)
        states: list[HourState] = []
        for hour in range(24):
            start_local = datetime(
                view_date.year, view_date.month, view_date.day, hour, 0, 0, tzinfo=tz
            )
            start_utc = start_local.astimezone(UTC)
            own = _hour_is_within_working(start_utc, city)
            if own and all(_hour_is_within_working(start_utc, other) for other in cities):
                states.append("overlap")
            elif own:
                states.append("working")
            else:
                states.append("outside")
        result[city.name] = states
    return result


def _working_intervals_utc(
    city: City, range_start: datetime, range_end: datetime
) -> list[tuple[datetime, datetime]]:
    """Each workday's 09:00–17:00 local, as UTC intervals clipped to the range."""
    tz = ZoneInfo(city.tz)
    first = range_start.astimezone(tz).date() - timedelta(days=1)
    last = range_end.astimezone(tz).date() + timedelta(days=1)
    intervals: list[tuple[datetime, datetime]] = []
    day = first
    while day <= last:
        if day.weekday() < 5:
            window_start = datetime(day.year, day.month, day.day, 9, 0, tzinfo=tz).astimezone(UTC)
            window_end = datetime(day.year, day.month, day.day, 17, 0, tzinfo=tz).astimezone(UTC)
            start = max(window_start, range_start)
            end = min(window_end, range_end)
            if start < end:
                intervals.append((start, end))
        day += timedelta(days=1)
    return intervals


def _intersect(
    a: list[tuple[datetime, datetime]], b: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    """Pairwise intersection of two sorted, disjoint interval lists."""
    out: list[tuple[datetime, datetime]] = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start < end:
            out.append((start, end))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def _merge_touching(
    intervals: list[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def overlap_windows(
    cities: Sequence[City], range_start: datetime, range_end: datetime
) -> list[OverlapWindow]:
    """Contiguous UTC intervals where every city is inside working hours."""
    if not cities or range_start >= range_end:
        return []
    intervals = _working_intervals_utc(cities[0], range_start, range_end)
    for city in cities[1:]:
        intervals = _intersect(intervals, _working_intervals_utc(city, range_start, range_end))
        if not intervals:
            break
    return [OverlapWindow(start, end) for start, end in _merge_touching(intervals)]


def overlap_hours(
    cities: Sequence[City], range_start: datetime, range_end: datetime
) -> float:
    """Total overlapping time in the range, in hours."""
    windows = overlap_windows(cities, range_start, range_end)
    total_seconds = sum((w.end_utc - w.start_utc).total_seconds() for w in windows)
    return total_seconds / 3600.0


def format_hours(hours: float) -> str:
    """Metric rendering, e.g. '5.0 h'."""
    return f"{hours:.1f} h"
