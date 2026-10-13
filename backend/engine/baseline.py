"""Personal baseline: each senior against their own normal.

BP: median of daily means over the 30 days BEFORE the recent 7-day window, so a drift in
progress doesn't pull its own baseline up. Steps: median of days with any steps.
A baseline can't make a dangerous number normal: red-flag floors sit above it.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import median

from .config import T
from .history import Day

B = T["baseline"]


def bp(days: dict[date, Day], today: date) -> dict:
    hi = today - timedelta(days=B["recent_days"])
    lo = hi - timedelta(days=B["window_days"])
    window = [d for d in days.values() if lo < d.date <= hi and d.bp]
    if len(window) < B["min_days"]:
        # Not enough history before the recent week: use everything before today, then the fallback.
        window = [d for d in days.values() if d.date < today and d.bp]
    if len(window) < B["min_days"]:
        fb = B["fallback_bp"]
        return {"systolic": fb["systolic"], "diastolic": fb["diastolic"], "days": len(window), "fallback": True}
    return {
        "systolic": round(median(d.sys for d in window), 1),
        "diastolic": round(median(d.dia for d in window), 1),
        "days": len(window),
        "fallback": False,
    }


def steps(days: dict[date, Day], today: date) -> float | None:
    """Excludes the last 14 days, so two weeks of low movement can't become the new normal."""
    hi = today - timedelta(days=14)
    lo = hi - timedelta(days=B["window_days"])
    vals = [d.steps for d in days.values() if lo <= d.date < hi and d.steps]
    if len(vals) < B["min_days"]:
        vals = [d.steps for d in days.values() if d.date < today and d.steps]
    return median(vals) if len(vals) >= B["min_days"] else None
