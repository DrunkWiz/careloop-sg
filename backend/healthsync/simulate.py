"""Stands in for the senior's phone: what Health Connect or Apple Health would hand over for one day.

A Fitbit writes steps in hourly blocks, a resting heart rate after waking, and last night's sleep with
its stages. An OMRON cuff writes each BP measurement. All synthetic: the numbers come from the demo's
script, or from a seeded random walk.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from .mapping import SGT

FITBIT = {"health_connect": "com.fitbit.FitbitMobile", "healthkit": ("Fitbit", "com.fitbit.FitbitMobile")}
OMRON = {"health_connect": "jp.co.omron.healthcare.omron_connect", "healthkit": ("OMRON connect", "jp.co.omron.healthcare.omronconnect")}
# How a day's steps spread over waking hours: a morning walk, the market, an evening stroll.
HOURLY = {7: 4, 8: 9, 9: 10, 10: 8, 11: 6, 12: 5, 13: 3, 14: 3, 15: 4, 16: 6, 17: 8, 18: 6, 19: 5, 20: 3, 21: 2}


def _iso(t: datetime) -> str:
    return t.astimezone(SGT).isoformat()


def _split(total: int, rng: random.Random) -> dict[int, int]:
    w = {h: v * rng.uniform(0.6, 1.4) for h, v in HOURLY.items()}
    s = sum(w.values())
    parts = {h: int(total * v / s) for h, v in w.items()}
    parts[9] += total - sum(parts.values())  # the remainder goes on the morning walk; the day still sums exactly
    return parts


def _sleep_segments(d: date, hours: float, rng: random.Random) -> tuple[datetime, datetime, list[tuple[datetime, datetime, str]]]:
    wake = datetime.combine(d, time(6, 30), SGT) + timedelta(minutes=rng.randint(-25, 35))
    awake_min = rng.randint(15, 40)
    start = wake - timedelta(hours=hours, minutes=awake_min)
    segs, t, cycle = [], start, ["light", "deep", "light", "rem"]
    i = 0
    awake_at = start + (wake - start) / 2
    while t < wake:
        if t >= awake_at and awake_min:  # one wake-up in the middle of the night
            e = min(t + timedelta(minutes=awake_min), wake)
            segs.append((t, e, "awake"))
            awake_min = 0
        else:
            e = min(t + timedelta(minutes=rng.randint(25, 55)), wake)
            segs.append((t, e, cycle[i % 4]))
            i += 1
        t = e
    return start, wake, segs


HC_STAGE = {"awake": 1, "light": 4, "deep": 5, "rem": 6}
HK_STAGE = {"awake": 2, "light": 3, "deep": 4, "rem": 5}


def phone_day(senior_id: str, d: date, *, platform: str, apps: tuple[str, ...] = ("fitbit",), steps: int | None = None,
              resting_hr: int | None = None, sleep_hours: float | None = None, bp: list[tuple[str, int, int]] = (),
              upto: datetime | None = None) -> list[dict]:
    """Records for day d as the platform would give them, up to `upto` (a sync during the day sees less)."""
    rng = random.Random(f"phone-{senior_id}-{d}")
    upto = upto or datetime.combine(d, time(23, 59), SGT)
    out: list[dict] = []
    hc = platform == "health_connect"

    def meta(rid: str, origin: dict) -> dict:
        if hc:
            return {"metadata": {"id": rid, "dataOrigin": {"packageName": origin[platform]}, "lastModifiedTime": _iso(upto)}}
        name, bundle = origin[platform]
        return {"uuid": rid, "sourceRevision": {"source": {"name": name, "bundleIdentifier": bundle}, "version": "5.05"}}

    if "fitbit" in apps and steps is not None:
        for h, n in _split(steps, rng).items():
            a = datetime.combine(d, time(h), SGT)
            b = a + timedelta(hours=1)
            if b > upto:
                break
            rid = f"{senior_id}-steps-{d}-{h:02d}"
            if hc:
                out.append({"recordType": "Steps", "startTime": _iso(a), "endTime": _iso(b), "startZoneOffset": "+08:00",
                            "count": n, **meta(rid, FITBIT)})
            else:
                out.append({"type": "HKQuantityTypeIdentifierStepCount", "startDate": _iso(a), "endDate": _iso(b),
                            "value": n, "unit": "count", **meta(rid, FITBIT)})

    if "fitbit" in apps and sleep_hours is not None:
        start, wake, segs = _sleep_segments(d, sleep_hours, rng)
        if wake <= upto:
            rid = f"{senior_id}-sleep-{d}"
            if hc:
                out.append({"recordType": "SleepSession", "startTime": _iso(start), "endTime": _iso(wake),
                            "stages": [{"startTime": _iso(a), "endTime": _iso(b), "stage": HC_STAGE[s]} for a, b, s in segs],
                            **meta(rid, FITBIT)})
            else:
                for j, (a, b, s) in enumerate(segs):
                    out.append({"type": "HKCategoryTypeIdentifierSleepAnalysis", "startDate": _iso(a), "endDate": _iso(b),
                                "value": HK_STAGE[s], **meta(f"{rid}-{j}", FITBIT)})

    if "fitbit" in apps and resting_hr is not None:
        t = datetime.combine(d, time(7, 15), SGT)
        if t <= upto:
            rid = f"{senior_id}-rhr-{d}"
            if hc:
                out.append({"recordType": "RestingHeartRate", "time": _iso(t), "beatsPerMinute": resting_hr, **meta(rid, FITBIT)})
            else:
                out.append({"type": "HKQuantityTypeIdentifierRestingHeartRate", "startDate": _iso(t), "endDate": _iso(t),
                            "value": resting_hr, "unit": "count/min", **meta(rid, FITBIT)})

    if "omron" in apps:
        for hhmm, s, di in bp:
            t = datetime.combine(d, time(*map(int, hhmm.split(":"))), SGT)
            if t > upto:
                continue
            rid = f"{senior_id}-bp-{d}-{hhmm.replace(':', '')}"
            if hc:
                out.append({"recordType": "BloodPressure", "time": _iso(t), "systolic": {"inMillimetersOfMercury": s},
                            "diastolic": {"inMillimetersOfMercury": di}, "bodyPosition": 2, "measurementLocation": 3,
                            **meta(rid, OMRON)})
            else:
                parts = [{"type": "HKQuantityTypeIdentifierBloodPressureSystolic", "value": s, "unit": "mmHg"},
                         {"type": "HKQuantityTypeIdentifierBloodPressureDiastolic", "value": di, "unit": "mmHg"}]
                out.append({"type": "HKCorrelationTypeIdentifierBloodPressure", "startDate": _iso(t), "endDate": _iso(t),
                            "objects": parts, **meta(rid, OMRON)})
    return out
