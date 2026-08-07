#!/usr/bin/env python3
"""Deterministic local-day date handling for briefs.

The brief's "day" is defined in the user's IANA timezone. These helpers make that boundary
logic testable and independent of the machine's local time. Stdlib only (zoneinfo, 3.9+).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

try:
    from zoneinfo import ZoneInfo  # Python 3.9+

    _HAVE_TZ = True
except Exception:  # pragma: no cover - environment without zoneinfo/tzdata
    _HAVE_TZ = False


def have_tz() -> bool:
    return _HAVE_TZ


def local_day_bounds(local_date: str, tz_name: str) -> Tuple[datetime, datetime]:
    """Return [start, end) as timezone-aware UTC datetimes for the given local calendar day."""
    if not _HAVE_TZ:
        raise RuntimeError("zoneinfo unavailable in this environment")
    tz = ZoneInfo(tz_name)
    y, m, d = (int(x) for x in local_date.split("-"))
    start_local = datetime(y, m, d, 0, 0, 0, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def in_local_day(iso_ts: str, local_date: str, tz_name: str) -> bool:
    """True if an ISO-8601 instant falls within the local calendar day in tz_name."""
    start, end = local_day_bounds(local_date, tz_name)
    dt = parse_iso(iso_ts)
    if dt.tzinfo is None:  # naive → interpret as the user's zone
        if not _HAVE_TZ:
            raise RuntimeError("zoneinfo unavailable in this environment")
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    dt = dt.astimezone(timezone.utc)
    return start <= dt < end


def parse_iso(iso_ts: str) -> datetime:
    """Parse ISO-8601, tolerating a trailing 'Z'."""
    return datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))


def local_date_for(iso_ts: str, tz_name: str) -> str:
    """The local calendar date (YYYY-MM-DD) of an instant, in tz_name."""
    if not _HAVE_TZ:
        raise RuntimeError("zoneinfo unavailable in this environment")
    return parse_iso(iso_ts).astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d")


def human_day(local_date: str) -> str:
    """'2026-08-07' -> 'Friday, August 7' (deterministic, locale-independent)."""
    y, m, d = (int(x) for x in local_date.split("-"))
    dt = datetime(y, m, d)
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    return f"{weekdays[dt.weekday()]}, {months[m - 1]} {d}"


if __name__ == "__main__":  # tiny manual check
    print(human_day("2026-08-07"))
    if _HAVE_TZ:
        print("in day:", in_local_day("2026-08-07T20:00:00Z", "2026-08-07", "America/Los_Angeles"))
