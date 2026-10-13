"""Tests for logic.py — mirrors the acceptance criteria in SPEC.md."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from logic import (
    CITIES,
    OverlapWindow,
    format_hours,
    get_city,
    hour_states,
    is_working,
    local_now,
    offset_badge,
    overlap_hours,
    overlap_windows,
)

UTC = timezone.utc
LONDON = get_city("London")
BALI = get_city("Bali")
NEW_YORK = get_city("New York")
SAN_FRANCISCO = get_city("San Francisco")
TOKYO = get_city("Tokyo")
DELHI = get_city("Delhi")
DUBLIN = get_city("Dublin")
REYKJAVIK = get_city("Reykjavik")

DAY = timedelta(days=1)


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def day_range(year: int, month: int, day: int) -> tuple[datetime, datetime]:
    return utc(year, month, day), utc(year, month, day) + DAY


# --- Catalog -----------------------------------------------------------------

def test_catalog_has_36_valid_cities():
    assert len(CITIES) == 36
    names = [city.name for city in CITIES]
    assert len(set(names)) == len(names)
    for city in CITIES:
        ZoneInfo(city.tz)  # every tz must resolve


def test_get_city():
    assert get_city("London").tz == "Europe/London"
    with pytest.raises(KeyError):
        get_city("Atlantis")


# --- Clocks ------------------------------------------------------------------

def test_local_clocks_match_mockup():
    now = datetime(2026, 10, 12, 15, 22, 21, tzinfo=UTC)
    london_local = local_now(LONDON, now)
    assert london_local.strftime("%H:%M:%S") == "16:22:21"
    assert offset_badge(london_local) == "↑ Monday · UTC+1"
    bali_local = local_now(BALI, now)
    assert bali_local.strftime("%H:%M:%S") == "23:22:21"
    assert offset_badge(bali_local) == "↑ Monday · UTC+8"


def test_offset_badge_negative_and_zero():
    now = utc(2026, 10, 13, 12, 0)  # Tuesday
    assert offset_badge(local_now(NEW_YORK, now)) == "↓ Tuesday · UTC-4"
    assert offset_badge(local_now(REYKJAVIK, now)) == "= Tuesday · UTC+0"


def test_local_clocks_half_hour_offset():
    now = utc(2026, 10, 13, 12, 0)
    assert offset_badge(local_now(DELHI, now)) == "↑ Tuesday · UTC+5:30"


# --- Working hours -----------------------------------------------------------

def test_is_working_boundaries():
    assert not is_working(datetime(2026, 10, 13, 8, 59))  # Tuesday
    assert is_working(datetime(2026, 10, 13, 9, 0))
    assert is_working(datetime(2026, 10, 13, 16, 59))
    assert not is_working(datetime(2026, 10, 13, 17, 0))
    assert not is_working(datetime(2026, 10, 17, 12, 0))  # Saturday


# --- 24-hour grid ------------------------------------------------------------

def test_grid_london_bali_matches_mockup():
    states = hour_states([LONDON, BALI], date(2026, 10, 13))
    london = states["London"]
    bali = states["Bali"]
    assert london[9] == "overlap"
    assert all(london[h] == "working" for h in range(10, 17))
    assert all(london[h] == "outside" for h in list(range(0, 9)) + list(range(17, 24)))
    assert bali[16] == "overlap"
    assert all(bali[h] == "working" for h in range(9, 16))
    assert all(bali[h] == "outside" for h in list(range(0, 9)) + list(range(17, 24)))


def test_weekend_grid_all_outside():
    states = hour_states([LONDON, BALI], date(2026, 10, 17))  # Saturday
    assert all(state == "outside" for state in states["London"])
    assert all(state == "outside" for state in states["Bali"])
    start, end = day_range(2026, 10, 17)
    assert overlap_hours([LONDON, BALI], start, end) == 0.0


def test_empty_selection():
    start, end = day_range(2026, 10, 13)
    assert hour_states([], date(2026, 10, 13)) == {}
    assert overlap_windows([], start, end) == []
    assert overlap_hours([], start, end) == 0.0


# --- Overlap windows ---------------------------------------------------------

def test_overlap_london_bali_single_day():
    start, end = day_range(2026, 10, 13)
    windows = overlap_windows([LONDON, BALI], start, end)
    assert windows == [OverlapWindow(utc(2026, 10, 13, 8), utc(2026, 10, 13, 9))]
    # London 09:00–10:00 local = Bali 16:00–17:00 local
    assert overlap_hours([LONDON, BALI], start, end) == 1.0


def test_overlap_next_7_days_matches_mockup_metric():
    start = utc(2026, 10, 13)
    end = start + 7 * DAY
    assert overlap_hours([LONDON, BALI], start, end) == 5.0  # 5 weekdays x 1 h
    assert format_hours(overlap_hours([LONDON, BALI], start, end)) == "5.0 h"


def test_no_overlap_san_francisco_tokyo():
    start = utc(2026, 10, 13)
    end = start + 7 * DAY
    assert overlap_windows([SAN_FRANCISCO, TOKYO], start, end) == []
    assert overlap_hours([SAN_FRANCISCO, TOKYO], start, end) == 0.0
    states = hour_states([SAN_FRANCISCO, TOKYO], date(2026, 10, 13))
    assert "working" in states["San Francisco"]  # blue cells remain
    assert "overlap" not in states["San Francisco"]
    assert "overlap" not in states["Tokyo"]


def test_same_offset_full_day_london_dublin():
    start, end = day_range(2026, 10, 13)
    assert overlap_hours([LONDON, DUBLIN], start, end) == 8.0
    states = hour_states([LONDON, DUBLIN], date(2026, 10, 13))
    assert all(states["London"][h] == "overlap" for h in range(9, 17))
    assert states["London"][8] == "outside"
    assert states["London"][17] == "outside"


def test_half_hour_offset_delhi():
    start, end = day_range(2026, 10, 13)
    windows = overlap_windows([LONDON, DELHI], start, end)
    assert windows == [OverlapWindow(utc(2026, 10, 13, 8), utc(2026, 10, 13, 11, 30))]
    assert overlap_hours([LONDON, DELHI], start, end) == 3.5
    assert format_hours(3.5) == "3.5 h"


def test_dst_shift_london_new_york():
    # EU DST ends 2026-10-25; US DST ends 2026-11-01.
    start, end = day_range(2026, 10, 20)  # both cities on DST
    assert overlap_windows([LONDON, NEW_YORK], start, end) == [
        OverlapWindow(utc(2026, 10, 20, 13), utc(2026, 10, 20, 16))
    ]
    assert overlap_hours([LONDON, NEW_YORK], start, end) == 3.0
    start, end = day_range(2026, 10, 27)  # London off DST, New York still on EDT
    assert overlap_windows([LONDON, NEW_YORK], start, end) == [
        OverlapWindow(utc(2026, 10, 27, 13), utc(2026, 10, 27, 17))
    ]
    assert overlap_hours([LONDON, NEW_YORK], start, end) == 4.0
    start, end = day_range(2026, 11, 3)  # both cities off DST
    assert overlap_windows([LONDON, NEW_YORK], start, end) == [
        OverlapWindow(utc(2026, 11, 3, 14), utc(2026, 11, 3, 17))
    ]
    assert overlap_hours([LONDON, NEW_YORK], start, end) == 3.0


def test_single_city_vacuous_overlap():
    start, end = day_range(2026, 10, 13)
    assert overlap_hours([LONDON], start, end) == 8.0
    states = hour_states([LONDON], date(2026, 10, 13))
    assert all(states["London"][h] == "overlap" for h in range(9, 17))


def test_format_hours():
    assert format_hours(5) == "5.0 h"
    assert format_hours(3.5) == "3.5 h"
    assert format_hours(0) == "0.0 h"
