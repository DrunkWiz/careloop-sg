"""Records as Health Connect and Apple Health hand them over, turned into CareLoop readings.

Health Connect (androidx.health.connect): StepsRecord, RestingHeartRateRecord, SleepSessionRecord and
BloodPressureRecord, each with metadata.id and metadata.dataOrigin.packageName.
Apple Health (HealthKit): HKQuantitySample, HKCategorySample and HKCorrelation, each with a uuid and
sourceRevision.source. Both arrive as JSON, the way a phone app would send them (see fixtures/).

Numbers are carried over, never changed. A unit is converted only where the record says what it is.
Unknown record types are skipped and counted, never guessed at.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))
PLATFORMS = ("health_connect", "healthkit")

# Health Connect sleep stages that count as asleep: 2 sleeping, 4 light, 5 deep, 6 REM (1 awake, 3 out of bed).
HC_ASLEEP = {2, 4, 5, 6}
# HealthKit HKCategoryValueSleepAnalysis values that count as asleep: 1 unspecified, 3 core, 4 deep, 5 REM.
HK_ASLEEP = {1, 3, 4, 5}

APPS = {  # package or bundle id -> the name people know
    "com.fitbit.FitbitMobile": "Fitbit",
    "com.google.android.apps.fitness": "Google Fit",
    "jp.co.omron.healthcare.omron_connect": "OMRON connect",
    "jp.co.omron.healthcare.omronconnect": "OMRON connect",
    "com.apple.health": "iPhone",
    "com.sec.android.app.shealth": "Samsung Health",
}


@dataclass
class Mapped:
    """What a batch of records became. Steps come as intervals, kept by day and record id, so an
    interval sent twice is counted once."""
    steps: dict[date, dict[str, int]] = field(default_factory=dict)
    steps_end: dict[date, datetime] = field(default_factory=dict)
    resting_hr: dict[date, tuple[datetime, int]] = field(default_factory=dict)
    sleep: dict[date, tuple[datetime, float]] = field(default_factory=dict)
    bp: list[dict] = field(default_factory=list)  # {"id", "time", "systolic", "diastolic"}
    apps: set[str] = field(default_factory=set)
    kinds: set[str] = field(default_factory=set)
    skipped: int = 0


def _t(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=SGT)).astimezone(SGT)


def _app(name_or_id: str | None) -> str | None:
    return APPS.get(name_or_id, name_or_id) if name_or_id else None


def _hours(segments: list[tuple[datetime, datetime]]) -> float:
    return round(sum((b - a).total_seconds() for a, b in segments) / 3600, 1)


def _add_steps(m: Mapped, rid: str, start: datetime, end: datetime, count: int) -> None:
    m.steps.setdefault(start.date(), {})[rid] = count
    m.steps_end[start.date()] = max(end, m.steps_end.get(start.date(), end))


def _add_hr(m: Mapped, t: datetime, bpm: int) -> None:
    if t.date() not in m.resting_hr or t >= m.resting_hr[t.date()][0]:
        m.resting_hr[t.date()] = (t, bpm)


def from_health_connect(records: list[dict], m: Mapped | None = None) -> Mapped:
    m = m or Mapped()
    for r in records:
        kind, meta = r.get("recordType"), r.get("metadata") or {}
        rid = meta.get("id")
        try:
            if kind == "Steps":
                _add_steps(m, rid, _t(r["startTime"]), _t(r["endTime"]), int(r["count"]))
                m.kinds.add("steps")
            elif kind == "RestingHeartRate":
                _add_hr(m, _t(r["time"]), int(r["beatsPerMinute"]))
                m.kinds.add("heart rate")
            elif kind == "SleepSession":
                end = _t(r["endTime"])
                stages = r.get("stages") or []
                asleep = [(_t(s["startTime"]), _t(s["endTime"])) for s in stages if s.get("stage") in HC_ASLEEP]
                m.sleep[end.date()] = (end, _hours(asleep) if stages else _hours([(_t(r["startTime"]), end)]))
                m.kinds.add("sleep")
            elif kind == "BloodPressure":
                m.bp.append({"id": rid, "time": _t(r["time"]), "systolic": round(r["systolic"]["inMillimetersOfMercury"]),
                             "diastolic": round(r["diastolic"]["inMillimetersOfMercury"])})
                m.kinds.add("blood pressure")
            else:
                m.skipped += 1
                continue
        except (KeyError, TypeError, ValueError):
            m.skipped += 1
            continue
        app = _app((meta.get("dataOrigin") or {}).get("packageName"))
        if app:
            m.apps.add(app)
    return m


def _hk(s: dict, unit: str) -> float:
    if s.get("unit") not in (unit, None):
        raise ValueError(f"unexpected unit {s.get('unit')}")
    return float(s["value"])


def from_healthkit(samples: list[dict], m: Mapped | None = None) -> Mapped:
    m = m or Mapped()
    sleep: dict[date, list[tuple[datetime, datetime]]] = {}
    for s in samples:
        kind = s.get("type")
        try:
            if kind == "HKQuantityTypeIdentifierStepCount":
                _add_steps(m, s["uuid"], _t(s["startDate"]), _t(s["endDate"]), int(_hk(s, "count")))
                m.kinds.add("steps")
            elif kind == "HKQuantityTypeIdentifierRestingHeartRate":
                _add_hr(m, _t(s["startDate"]), round(_hk(s, "count/min")))
                m.kinds.add("heart rate")
            elif kind == "HKCategoryTypeIdentifierSleepAnalysis":
                if int(s["value"]) in HK_ASLEEP:
                    end = _t(s["endDate"])
                    sleep.setdefault(end.date(), []).append((_t(s["startDate"]), end))
                m.kinds.add("sleep")
            elif kind == "HKCorrelationTypeIdentifierBloodPressure":
                parts = {o["type"]: o for o in s["objects"]}
                m.bp.append({"id": s["uuid"], "time": _t(s["startDate"]),
                             "systolic": round(_hk(parts["HKQuantityTypeIdentifierBloodPressureSystolic"], "mmHg")),
                             "diastolic": round(_hk(parts["HKQuantityTypeIdentifierBloodPressureDiastolic"], "mmHg"))})
                m.kinds.add("blood pressure")
            else:
                m.skipped += 1
                continue
        except (KeyError, TypeError, ValueError):
            m.skipped += 1
            continue
        src = (s.get("sourceRevision") or {}).get("source") or {}
        app = _app(src.get("bundleIdentifier")) or src.get("name")
        if app:
            m.apps.add(app)
    for d, segs in sleep.items():
        m.sleep[d] = (max(b for _, b in segs), _hours(segs))
    return m


def parse(platform: str, records: list[dict]) -> Mapped:
    if platform == "health_connect":
        return from_health_connect(records)
    if platform == "healthkit":
        return from_healthkit(records)
    raise ValueError(f"unknown platform {platform}")


def to_readings(senior_id: str, m: Mapped, steps_by_day: dict[date, dict[str, int]] | None = None) -> list[dict]:
    """CareLoop readings. Steps, heart rate and sleep get one reading a day with a fixed id, so each sync
    replaces the last. `steps_by_day` is every interval seen so far each day (this batch and earlier ones)."""
    out = []
    for d, by_id in (steps_by_day if steps_by_day is not None else m.steps).items():
        end = m.steps_end.get(d) or datetime(d.year, d.month, d.day, 23, 59, tzinfo=SGT)
        out.append({"id": f"hs-{senior_id}-steps-{d}", "senior_id": senior_id, "time": end.isoformat(), "kind": "steps",
                    "values": {"count": sum(by_id.values())}, "source": "watch", "confidence": 1})
    for d, (t, bpm) in m.resting_hr.items():
        out.append({"id": f"hs-{senior_id}-hr-{d}", "senior_id": senior_id, "time": t.isoformat(), "kind": "hr",
                    "values": {"bpm": bpm}, "source": "watch", "confidence": 1})
    for d, (t, hours) in m.sleep.items():
        out.append({"id": f"hs-{senior_id}-sleep-{d}", "senior_id": senior_id, "time": t.isoformat(), "kind": "sleep",
                    "values": {"hours": hours}, "source": "watch", "confidence": 1})
    for b in m.bp:
        out.append({"id": f"hs-{senior_id}-bp-{b['id']}", "senior_id": senior_id, "time": b["time"].isoformat(), "kind": "bp",
                    "values": {"systolic": b["systolic"], "diastolic": b["diastolic"]}, "source": "cuff", "confidence": 1})
    return out
