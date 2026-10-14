"""Store a sync from the senior's phone as readings, and remember what is connected.

Every reading passes the trust check like any other. The engine is not run here: the API runs the day
after a sync that touches today, the same as after any new reading.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from backend.engine import trust_check

from .mapping import Mapped, parse, to_readings

PLATFORM_NAMES = {"health_connect": "Health Connect", "healthkit": "Apple Health"}


def _key(senior_id: str) -> str:
    return f"healthsync:{senior_id}"


def status(store, senior_id: str) -> dict | None:
    v = store.setting(_key(senior_id))
    return json.loads(v) if v else None


def _drop_future(m: Mapped, now: datetime) -> int:
    """A record from the future (a wrong phone clock) is skipped, not moved."""
    late = now + timedelta(hours=1)
    n = 0
    for d in [d for d in m.steps if d > now.date()]:
        n += len(m.steps.pop(d))
        m.steps_end.pop(d, None)
    for table in (m.resting_hr, m.sleep):
        for d in [d for d, (t, _) in table.items() if t > late]:
            table.pop(d)
            n += 1
    keep = [b for b in m.bp if b["time"] <= late]
    n += len(m.bp) - len(keep)
    m.bp = keep
    return n


def ingest(store, senior_id: str, platform: str, records: list[dict], *, now: datetime) -> dict:
    m = parse(platform, records)
    skipped = m.skipped + _drop_future(m, now)

    # Steps arrive as intervals. A phone may send the whole day again or only what's new, so merge them
    # with what earlier syncs sent, by record id, and total that.
    merged: dict[date, dict[str, int]] = {}
    for d, by_id in m.steps.items():
        key = f"healthsync-steps:{senior_id}:{d}"
        seen = json.loads(store.setting(key) or "{}")
        seen.update(by_id)
        store.set_setting(key, json.dumps(seen))
        merged[d] = seen

    readings = to_readings(senior_id, m, merged)
    for r in readings:
        store.put("reading", {**r, "trust": trust_check(r)})

    prev = status(store, senior_id) or {}
    st = {
        "platform": platform,
        "platform_name": PLATFORM_NAMES[platform],
        "apps": sorted(set(prev.get("apps", [])) | m.apps) if prev.get("platform") == platform else sorted(m.apps),
        "kinds": sorted(set(prev.get("kinds", [])) | m.kinds) if prev.get("platform") == platform else sorted(m.kinds),
        "last_sync": now.isoformat(),
        "last_batch": {"records": len(records), "readings": len(readings), "skipped": skipped},
    }
    store.set_setting(_key(senior_id), json.dumps(st))
    days = sorted({r["time"][:10] for r in readings})
    return {"status": st, "readings": readings, "days": days, "skipped": skipped}


def recent(store, senior_id: str, today: date, days: int = 7) -> list[dict]:
    """Day by day, what came from the phone: steps, resting heart rate, sleep and synced BP readings."""
    lo = (today - timedelta(days=days - 1)).isoformat()
    rows = {(today - timedelta(i)).isoformat(): {"date": (today - timedelta(i)).isoformat(), "steps": None, "resting_hr": None,
                                                  "sleep_hours": None, "bp": []} for i in range(days)}
    for r in store.list("reading", senior_id=senior_id, day_from=lo, day_to=today.isoformat()):
        if not r["id"].startswith(f"hs-{senior_id}-"):
            continue
        row = rows.get(r["time"][:10])
        if row is None or not (r.get("trust") or {}).get("ok", True):
            continue
        v = r["values"]
        if r["kind"] == "steps":
            row["steps"] = v["count"]
        elif r["kind"] == "hr":
            row["resting_hr"] = v["bpm"]
        elif r["kind"] == "sleep":
            row["sleep_hours"] = v["hours"]
        elif r["kind"] == "bp":
            row["bp"].append({"time": r["time"], "systolic": v["systolic"], "diastolic": v["diastolic"]})
    return sorted(rows.values(), key=lambda x: x["date"])
