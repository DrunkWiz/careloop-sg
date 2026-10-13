"""Trust check: every reading passes here first. It flags; it never fixes a number.

Flags:
  no_reading   nothing usable was given
  impossible   outside any human range
  swapped      systolic <= diastolic, but the other way round would be plausible
  units        glucose in the wrong unit (7.2 entered as mg/dL is surely mmol/L)
A flagged reading is not used for the baseline or for drift. It triggers rung 1 (ask to
re-measure or confirm), except that red-flag floors are checked on both orders of a swapped
pair, because 112/186 is far more likely 186/112 than a typo for something safe.
"""
from __future__ import annotations

from .config import T

TR = T["trust"]


def _in(v, lo_hi) -> bool:
    lo, hi = lo_hi
    return v is not None and lo <= v <= hi


def check(reading: dict) -> dict:
    kind, v = reading.get("kind"), reading.get("values") or {}
    flags: list[str] = []
    if kind == "bp":
        s, d = v.get("systolic"), v.get("diastolic")
        if s is None or d is None:
            flags.append("no_reading")
        elif s <= d:
            flags.append("swapped" if _in(d, TR["systolic_range"]) and _in(s, TR["diastolic_range"]) else "impossible")
        elif not (_in(s, TR["systolic_range"]) and _in(d, TR["diastolic_range"])):
            flags.append("impossible")
        p = v.get("pulse")
        if p is not None and not _in(p, TR["heart_rate_range"]):
            flags.append("impossible")
    elif kind == "hr":
        if not _in(v.get("bpm"), TR["heart_rate_range"]):
            flags.append("impossible" if v.get("bpm") is not None else "no_reading")
    elif kind == "steps":
        c = v.get("count")
        if c is None:
            flags.append("no_reading")
        elif c < 0 or c > TR["steps_max"]:
            flags.append("impossible")
    elif kind == "glucose":
        val, unit = v.get("value"), (v.get("unit") or "").lower().replace(" ", "")
        if val is None:
            flags.append("no_reading")
        elif unit in ("mg/dl", "mgdl"):
            if _in(val, TR["glucose_mmol_range"]) and val < TR["glucose_mgdl_range"][0]:
                flags.append("units")
            elif not _in(val, TR["glucose_mgdl_range"]):
                flags.append("impossible")
        elif unit in ("mmol/l", "mmol"):
            if _in(val, TR["glucose_mgdl_range"]) and val > TR["glucose_mmol_range"][1]:
                flags.append("units")
            elif not _in(val, TR["glucose_mmol_range"]):
                flags.append("impossible")
        else:
            flags.append("units")
    return {"ok": not flags, "flags": sorted(set(flags))}


def red_flag_pairs(reading: dict) -> list[tuple[int, int]]:
    """BP pairs to test against red-flag floors: as given, and swapped back if flagged swapped."""
    v = reading.get("values") or {}
    s, d = v.get("systolic"), v.get("diastolic")
    if reading.get("kind") != "bp" or s is None or d is None:
        return []
    flags = (reading.get("trust") or check(reading))["flags"]
    if "impossible" in flags:
        return []
    return [(d, s)] if "swapped" in flags else [(s, d)]
