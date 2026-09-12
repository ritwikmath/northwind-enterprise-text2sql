"""Turn a symbolic time period into concrete bounds.

Semantic analysis records a period the way the user said it — "last month", "next 30
days" — and deliberately does not work out what that means, because the model that
reads the question has no reliable calendar. Resolving it is arithmetic, so it happens
here, in code, against one `now` passed in by the caller.

Bounds are half-open: `start <= column < end`. A closed upper bound is the classic
off-by-a-day — `BETWEEN '2026-01-01' AND '2026-01-31'` silently drops everything
timestamped later than midnight on the 31st — and half-open intervals tile without
gaps or overlap, so consecutive periods can be compared without double counting.

"Last month" means the previous *complete* calendar month, not the last 30 days. A
duration the user actually stated ("last 30 days") is measured back from now instead.
"""

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Literal

Unit = Literal["day", "week", "month", "quarter", "year"]

Bounds = tuple[datetime | None, datetime | None]


def __days_in_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def __shift_months(moment: datetime, count: int) -> datetime:
    """Move by whole months, clamping the day to one the target month has.

    31 January shifted back a month is 31 December, but forward a month it can only be
    28 or 29 February. Clamping is what every calendar does and what the user means.
    """
    index = moment.month - 1 + count
    year = moment.year + index // 12
    month = index % 12 + 1
    return moment.replace(year=year, month=month, day=min(moment.day, __days_in_month(year, month)))


def shift(moment: datetime, count: int, unit: Unit) -> datetime:
    """Move `moment` by `count` units, forwards or backwards."""
    if unit == "day":
        return moment + timedelta(days=count)
    if unit == "week":
        return moment + timedelta(weeks=count)
    if unit == "month":
        return __shift_months(moment, count)
    if unit == "quarter":
        return __shift_months(moment, count * 3)
    return __shift_months(moment, count * 12)


def start_of(moment: datetime, unit: Unit) -> datetime:
    """The first instant of the unit that `moment` falls in. Weeks start on Monday."""
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "day":
        return midnight
    if unit == "week":
        return midnight - timedelta(days=midnight.weekday())
    if unit == "month":
        return midnight.replace(day=1)
    if unit == "quarter":
        return midnight.replace(month=(midnight.month - 1) // 3 * 3 + 1, day=1)
    return midnight.replace(month=1, day=1)


def resolve(time_range, now: datetime) -> Bounds:
    """The half-open bounds a `BoundTimeRange` stands for, or `(None, None)`.

    `(None, None)` means the period said too little to place on a calendar — a relative
    expression with no unit, say. The caller drops the period rather than guessing at
    it; a query silently scoped to the wrong span is worse than one not scoped at all.
    A single bound is legitimate and is returned as such: "since March" has no end.
    """
    kind = time_range.type
    unit: Unit | None = time_range.unit
    count = time_range.value

    if kind in ("absolute", "between"):
        return time_range.start_date, time_range.end_date

    if kind == "relative":
        if count and unit:
            return shift(now, -count, unit), now
        if unit:
            # The previous complete unit: "last month" excludes the current one.
            end = start_of(now, unit)
            return shift(end, -1, unit), end
        return None, None

    if kind == "upcoming":
        if count and unit:
            return now, shift(now, count, unit)
        if unit:
            start = shift(start_of(now, unit), 1, unit)
            return start, shift(start, 1, unit)
        return None, None

    return None, None
