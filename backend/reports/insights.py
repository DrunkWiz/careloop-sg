"""Patterns in a senior's own data, for the caregiver app. Owner: Nathan.

Plain statistics over the engine's daily history (backend/engine/history.py): trends, this week against
last, weekday patterns, and simple comparisons (BP on social days against other days). No model is
involved and nothing here picks a rung or contacts anyone: the rules do that. Every finding says how much
data it rests on, and a finding is only made when there is enough (MIN_* below). These are patterns in
one person's data, not medical conclusions, and the app says so.

Standard library only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, median

from backend.engine import baseline as base
from backend.engine.history import build

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WEEKDAY_NAMES = ("Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays")

MIN_TREND_DAYS = 10  # BP readings needed before calling a trend
TREND_MMHG_PER_WEEK = 2.0  # slope that counts as rising or falling
WEEK_CHANGE_MMHG = 8  # this week against last that is worth a line
MIN_GROUP_DAYS = 5  # days in each group before comparing two groups
GROUP_DIFF_MMHG = 5  # difference between groups that is worth a line
MIN_WEEKDAY_MISSES = 2
LOW_STEPS_SHARE = 0.7  # last week's steps under this share of usual counts as moving less


def _slope_per_week(points: list[tuple[int, float]]) -> float | None:
    """Least-squares slope, in units per week. points = (day index, value)."""
    if len(points) < 2:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in points) / sxx * 7


def _avg(xs: list[float]) -> float | None:
    return round(mean(xs), 1) if xs else None


def _minutes(t: str) -> int:
    h, m = t.split(":")[:2]
    return int(h) * 60 + int(m)


def _clock(mins: float) -> str:
    h, m = divmod(int(round(mins)), 60)
    return f"{h % 12 or 12}:{m:02d} {'am' if h < 12 else 'pm'}"


def insights(store, senior: dict, today: date, *, days: int = 30, numbers: bool = True, activity: bool = True) -> dict:
    """numbers=False drops readings (the senior shares the digest only); activity=False drops steps and contact."""
    days = max(14, min(days, 90))
    hist = build(store, senior, today, days=days + 30)  # the extra month feeds the baseline
    window = [hist[today - timedelta(i)] for i in range(days - 1, -1, -1)]
    last7, prev7 = window[-7:], window[-14:-7]
    bpb = base.bp(hist, today)
    findings: list[dict] = []

    def find(fid: str, tone: str, title: str, detail: str, n: int) -> None:
        findings.append({"id": fid, "tone": tone, "title": title, "detail": detail, "n": n})

    # --- blood pressure ---------------------------------------------------------------------
    bp_days = [(i, d) for i, d in enumerate(window) if d.sys is not None]
    slope = _slope_per_week([(i, d.sys) for i, d in bp_days])
    l7 = [d for d in last7 if d.sys is not None]
    p7 = [d for d in prev7 if d.sys is not None]
    l7s, p7s = _avg([d.sys for d in l7]), _avg([d.sys for d in p7])
    change = round(l7s - p7s, 1) if l7s is not None and p7s is not None else None
    over140 = sum(1 for _, d in bp_days if d.sys > 140)
    flagged = sum(len(d.bp_flagged) for d in window)

    if len(bp_days) >= MIN_TREND_DAYS and slope is not None:
        if slope >= TREND_MMHG_PER_WEEK:
            trend = "rising"
            find("bp_trend", "watch", "Blood pressure is trending up",
                 f"About {slope:+.0f} mmHg a week over {len(bp_days)} readings." if numbers else
                 f"A steady rise across {len(bp_days)} readings.", len(bp_days))
        elif slope <= -TREND_MMHG_PER_WEEK:
            trend = "falling"
            find("bp_trend", "good", "Blood pressure is trending down",
                 f"About {slope:+.0f} mmHg a week over {len(bp_days)} readings." if numbers else
                 f"A steady fall across {len(bp_days)} readings.", len(bp_days))
        else:
            trend = "steady"
            find("bp_trend", "good", "Blood pressure is steady",
                 (f"No clear rise or fall across {len(bp_days)} readings, around their usual {bpb['systolic']:.0f}/{bpb['diastolic']:.0f}."
                  if numbers and not bpb["fallback"] else f"No clear rise or fall across {len(bp_days)} readings."), len(bp_days))
    else:
        trend = "unclear"
        find("bp_trend", "neutral", "Not enough readings for a trend yet",
             f"{len(bp_days)} readings in {days} days. CareLoop needs {MIN_TREND_DAYS}.", len(bp_days))

    if change is not None and abs(change) >= WEEK_CHANGE_MMHG and len(l7) >= 3 and len(p7) >= 3:
        find("bp_week", "watch" if change > 0 else "good",
             f"This week is {'higher' if change > 0 else 'lower'} than last week",
             f"Top number averaged {l7s:.0f} this week against {p7s:.0f} last week." if numbers else
             "A clear change from last week.", len(l7) + len(p7))

    if flagged >= 2:
        find("bp_quality", "neutral", f"{flagged} readings looked wrong",
             "They failed the trust check (for example, the numbers swapped), so CareLoop asked to measure again "
             "and left them out.", flagged)

    # --- medicine ---------------------------------------------------------------------------
    reported = [d for d in window if d.taken or d.missed]
    taken = sum(d.taken for d in window)
    missed = sum(d.missed for d in window)
    by_weekday = []
    for w in range(7):
        wd = [d for d in window if d.date.weekday() == w]
        by_weekday.append({"day": WEEKDAYS[w], "missed": sum(d.missed for d in wd), "reported": sum(1 for d in wd if d.taken or d.missed)})
    streak = 0
    for d in reversed(window):
        if d.taken and not d.missed:
            streak += 1
        elif d.taken or d.missed:
            break
    if reported:
        rate = taken / len(reported)
        if rate >= 0.95:
            find("adherence", "good", "Taking medicine reliably", f"Taken on {taken} of {len(reported)} days with a report.", len(reported))
        elif rate < 0.8:
            find("adherence", "watch", "Missing medicine often", f"Taken on {taken} of {len(reported)} days with a report; missed on {missed}.", len(reported))
        worst = max(range(7), key=lambda w: by_weekday[w]["missed"])
        wb = by_weekday[worst]
        if wb["missed"] >= MIN_WEEKDAY_MISSES and wb["reported"] and wb["missed"] / wb["reported"] >= 0.5:
            find("adherence_weekday", "watch", f"Misses cluster on {WEEKDAY_NAMES[worst]}",
                 f"Missed on {wb['missed']} of {wb['reported']} {WEEKDAY_NAMES[worst]}. A routine change that day may help.", wb["reported"])
        # BP the day after a missed dose, against other days
        after_miss = [hist[d.date + timedelta(1)].sys for d in window[:-1] if d.missed and hist.get(d.date + timedelta(1)) and hist[d.date + timedelta(1)].sys]
        others = [d.sys for d in window if d.sys is not None]
        if numbers and len(after_miss) >= 3 and len(others) >= MIN_GROUP_DAYS:
            diff = mean(after_miss) - mean(others)
            if diff >= GROUP_DIFF_MMHG:
                find("bp_after_miss", "watch", "BP is higher the day after a missed dose",
                     f"About {diff:.0f} mmHg higher on {len(after_miss)} such days. A pattern in their data, not a diagnosis.", len(after_miss))

    # --- activity and contact ---------------------------------------------------------------
    act = None
    if activity:
        stb = base.steps(hist, today)
        s7 = [d.steps for d in last7 if d.steps is not None]
        s7avg = round(mean(s7)) if s7 else None
        social7 = sum(d.social for d in last7)
        socialp = sum(d.social for d in prev7)
        rain7 = sum(1 for d in last7 if d.rain_mm and d.rain_mm >= 1)
        act = {
            "steps": [{"date": d.date.isoformat(), "steps": d.steps} for d in window],
            "steps_baseline": round(stb) if stb else None,
            "steps_last7_avg": s7avg,
            "social_days_last7": social7,
            "social_days_prev7": socialp,
        }
        if stb and s7avg is not None and len(s7) >= 4:
            share = s7avg / stb
            if share < LOW_STEPS_SHARE:
                find("steps", "watch" if rain7 < 3 else "neutral", "Moving less than usual",
                     f"About {s7avg:,} steps a day this week against their usual {round(stb):,}."
                     + (f" {rain7} rainy days explain some of it." if rain7 >= 2 else ""), len(s7))
            elif share >= 0.9:
                find("steps", "good", "Moving as much as usual", f"About {s7avg:,} steps a day against their usual {round(stb):,}.", len(s7))
        if social7 >= 2:
            find("social", "good", f"Saw friends or family on {social7} days this week",
                 f"Last week: {socialp}." if socialp != social7 else "The same as last week.", 7)
        elif social7 == 0 and sum(1 for d in last7 if d.replies) >= 4:
            find("social", "watch", "No time with others this week",
                 "Their check-ins mention no friends or family on any day.", 7)
        if numbers:
            soc = [d.sys for d in window if d.sys is not None and d.social]
            non = [d.sys for d in window if d.sys is not None and not d.social]
            if len(soc) >= MIN_GROUP_DAYS and len(non) >= MIN_GROUP_DAYS:
                diff = mean(non) - mean(soc)
                if abs(diff) >= GROUP_DIFF_MMHG:
                    find("bp_social", "good" if diff > 0 else "neutral",
                         f"BP tends to be {'lower' if diff > 0 else 'higher'} on social days",
                         f"About {abs(diff):.0f} mmHg {'lower' if diff > 0 else 'higher'} on {len(soc)} days with friends or family, "
                         f"against {len(non)} other days. A pattern in their data, not a cause.", len(soc) + len(non))

    # --- check-ins --------------------------------------------------------------------------
    replied = sum(1 for d in window if d.replies)
    usual = senior.get("usual_checkin_time", "08:00")
    first_times = []
    for c in store.list("checkin", senior_id=senior["id"], day_from=window[0].date.isoformat(), day_to=today.isoformat()):
        try:
            first_times.append((c["time"][:10], _minutes(datetime.fromisoformat(c["time"]).strftime("%H:%M"))))
        except ValueError:
            continue
    per_day = {}
    for day_s, mins in first_times:
        per_day[day_s] = min(per_day.get(day_s, 24 * 60), mins)
    med = median(per_day.values()) if per_day else None
    if replied >= days * 0.9:
        find("checkins", "good", "Checks in almost every day", f"Replied on {replied} of {days} days.", days)
    elif replied <= days * 0.6:
        find("checkins", "watch", "Often doesn't reply", f"Replied on {replied} of {days} days.", days)
    if med is not None and med - _minutes(usual) >= 60:
        find("checkin_time", "neutral", "Checking in later than usual",
             f"Usually around {_clock(med)}, against the {_clock(_minutes(usual))} they set.", len(per_day))

    rain_days = sum(1 for d in window if d.rain_mm and d.rain_mm >= 1)
    haze_days = sum(1 for d in window if d.psi and d.psi > 100)
    if haze_days:
        find("haze", "neutral", f"{haze_days} hazy day{'s' if haze_days > 1 else ''}",
             "CareLoop suggested indoor options and did not count those quiet days against them.", haze_days)

    order = {"watch": 0, "good": 1, "neutral": 2}
    findings.sort(key=lambda f: order[f["tone"]])
    return {
        "period": {"from": window[0].date.isoformat(), "to": today.isoformat(), "days": days},
        "bp": {
            "shared": numbers,
            "series": [{"date": d.date.isoformat(), "systolic": round(d.sys) if d.sys else None, "diastolic": round(d.dia) if d.dia else None}
                       for d in window] if numbers else [],
            "baseline": {"systolic": bpb["systolic"], "diastolic": bpb["diastolic"], "fallback": bpb["fallback"]} if numbers else None,
            "last7_systolic": l7s if numbers else None,
            "prev7_systolic": p7s if numbers else None,
            "slope_per_week": round(slope, 1) if slope is not None and numbers else None,
            "trend": trend,
            "days_over_140": over140 if numbers else None,
            "readings_days": len(bp_days),
        },
        "adherence": {
            "reported_days": len(reported), "taken_days": taken, "missed_days": missed, "streak_days": streak,
            "by_weekday": by_weekday,
            "calendar": [{"date": d.date.isoformat(), "pills": "taken" if d.taken else "missed" if d.missed else None} for d in window],
        },
        "activity": act,
        "checkins": {"replied_days": replied, "days": days, "usual_time": usual, "median_first_time": _clock(med) if med is not None else None},
        "context": {"rain_days": rain_days, "haze_days": haze_days, "festival_days": sum(1 for d in window if d.festival)},
        "findings": findings,
        "note": "Patterns in their own data, worked out with simple statistics. Not a diagnosis. Synthetic data in the demo.",
    }
