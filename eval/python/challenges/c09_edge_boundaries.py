"""
CHALLENGE: Date/Time Range Calculator
CATEGORY: edge_cases
DIFFICULTY: 2
POINTS: 5
WHY: Models get timezone and DST handling wrong. They confuse naive and aware datetimes,
     ignore DST transitions, and calculate durations using timedelta when they should use
     calendar math. Date/time is where "works in tests, breaks in production" lives.
"""

PROMPT = """
Write functions for working with date/time ranges correctly.

```python
from datetime import datetime, date
from zoneinfo import ZoneInfo

def business_days_between(start: date, end: date, holidays: list[date] = None) -> int:
    \"\"\"
    Count business days between start and end (inclusive of start, exclusive of end).
    Business days are Monday-Friday, excluding dates in the holidays list.
    If start >= end, return 0.
    \"\"\"

def overlap_minutes(
    start1: datetime, end1: datetime,
    start2: datetime, end2: datetime,
) -> int:
    \"\"\"
    Calculate the overlap in whole minutes between two time ranges.
    All datetimes are timezone-aware.
    Returns 0 if no overlap.
    Handles DST transitions correctly (use actual elapsed time, not wall clock math).
    \"\"\"

def add_business_days(start: date, days: int, holidays: list[date] = None) -> date:
    \"\"\"
    Add `days` business days to start date.
    Skip weekends and holidays.
    If days is 0, return start (even if start is a weekend/holiday).
    If days is negative, count backwards.
    \"\"\"
```
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


def load():
    mod = importlib.import_module("solutions.c09_edge_boundaries")
    return mod.business_days_between, mod.overlap_minutes, mod.add_business_days


class TestBusinessDays:
    """2 points."""

    def test_simple_week(self):
        """(0.5 pt) Monday to next Monday = 5 business days."""
        biz_days, _, _ = load()
        # 2025-01-06 is Monday, 2025-01-13 is next Monday
        assert biz_days(date(2025, 1, 6), date(2025, 1, 13)) == 5

    def test_with_holidays(self):
        """(0.5 pt) Holidays reduce count."""
        biz_days, _, _ = load()
        # Remove Wednesday
        holidays = [date(2025, 1, 8)]
        assert biz_days(date(2025, 1, 6), date(2025, 1, 13), holidays) == 4

    def test_start_after_end(self):
        """(0.5 pt) Returns 0 when start >= end."""
        biz_days, _, _ = load()
        assert biz_days(date(2025, 1, 10), date(2025, 1, 6)) == 0
        assert biz_days(date(2025, 1, 6), date(2025, 1, 6)) == 0

    def test_weekend_only_range(self):
        """(0.5 pt) Saturday to Monday = 0 business days."""
        biz_days, _, _ = load()
        # 2025-01-11 is Saturday, 2025-01-13 is Monday
        assert biz_days(date(2025, 1, 11), date(2025, 1, 13)) == 0


class TestOverlapMinutes:
    """2 points."""

    def test_full_overlap(self):
        """(0.5 pt) One range contains the other."""
        _, overlap, _ = load()
        tz = ZoneInfo("UTC")
        r = overlap(
            datetime(2025, 1, 1, 9, 0, tzinfo=tz), datetime(2025, 1, 1, 17, 0, tzinfo=tz),
            datetime(2025, 1, 1, 10, 0, tzinfo=tz), datetime(2025, 1, 1, 12, 0, tzinfo=tz),
        )
        assert r == 120

    def test_no_overlap(self):
        """(0.5 pt) Non-overlapping ranges return 0."""
        _, overlap, _ = load()
        tz = ZoneInfo("UTC")
        r = overlap(
            datetime(2025, 1, 1, 9, 0, tzinfo=tz), datetime(2025, 1, 1, 10, 0, tzinfo=tz),
            datetime(2025, 1, 1, 10, 0, tzinfo=tz), datetime(2025, 1, 1, 11, 0, tzinfo=tz),
        )
        assert r == 0

    def test_dst_spring_forward(self):
        """(1 pt) DST transition: 2:00 AM doesn't exist, overlap should use real elapsed time."""
        _, overlap, _ = load()
        # US/Eastern springs forward at 2:00 AM on March 9, 2025
        # 1:00 AM -> 3:00 AM (skipping 2:00-3:00)
        tz = ZoneInfo("US/Eastern")
        # Range 1: 1:00 AM to 4:00 AM Eastern = 2 real hours (1h before + 1h after DST gap)
        # Range 2: 1:30 AM to 3:30 AM Eastern = 1.5 real hours
        # Overlap: 1:30 AM to 3:30 AM within 1:00-4:00 = 1.5 real hours = 90 real minutes
        r = overlap(
            datetime(2025, 3, 9, 1, 0, tzinfo=tz), datetime(2025, 3, 9, 4, 0, tzinfo=tz),
            datetime(2025, 3, 9, 1, 30, tzinfo=tz), datetime(2025, 3, 9, 3, 30, tzinfo=tz),
        )
        assert r == 90


class TestAddBusinessDays:
    """1 point."""

    def test_add_days(self):
        """(0.5 pt) Add 3 business days from Wednesday = Monday."""
        _, _, add_biz = load()
        # 2025-01-08 (Wed) + 3 business days = 2025-01-13 (Mon)
        assert add_biz(date(2025, 1, 8), 3) == date(2025, 1, 13)

    def test_negative_days(self):
        """(0.5 pt) Subtract business days."""
        _, _, add_biz = load()
        # 2025-01-13 (Mon) - 3 business days = 2025-01-08 (Wed)
        assert add_biz(date(2025, 1, 13), -3) == date(2025, 1, 8)
