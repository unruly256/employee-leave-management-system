"""Day counting. Leave days are working days (Mon-Fri, minus public holidays) by default."""
from datetime import date, timedelta

from django.conf import settings

# Fixed-date Uganda public holidays. Moveable ones (Good Friday, Easter Monday,
# Eid al-Fitr, Eid al-Adha) change yearly: add them in settings.LEAVE_EXTRA_HOLIDAYS.
FIXED_HOLIDAYS = {
    (1, 1), (1, 26), (2, 16), (3, 8), (5, 1), (6, 3), (6, 9), (10, 9), (12, 25), (12, 26),
}


def _extra_holidays():
    return {date.fromisoformat(iso) for iso in getattr(settings, "LEAVE_EXTRA_HOLIDAYS", [])}


def is_holiday(d, extras=None):
    extras = _extra_holidays() if extras is None else extras
    return (d.month, d.day) in FIXED_HOLIDAYS or d in extras


def holidays_for_years(years):
    """Sorted ISO dates of every public holiday in the given years (used by the browser preview)."""
    found = {date(y, m, d) for y in years for m, d in FIXED_HOLIDAYS}
    found |= {d for d in _extra_holidays() if d.year in set(years)}
    return sorted(d.isoformat() for d in found)


def count_days(start, end):
    """Number of leave days between start and end, both inclusive."""
    if end < start:
        return 0
    if getattr(settings, "LEAVE_DAY_BASIS", "working") == "calendar":
        return (end - start).days + 1
    extras = _extra_holidays()
    total, d = 0, start
    while d <= end:
        if d.weekday() < 5 and not is_holiday(d, extras):
            total += 1
        d += timedelta(days=1)
    return total
