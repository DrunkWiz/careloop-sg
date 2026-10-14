"""One summary per day per senior: what the rules read. Built from readings, check-ins and EnvDays."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean

from .config import festival_on
from .trust import check, red_flag_pairs


@dataclass
class Day:
    date: date
    bp: list[tuple[int, int]] = field(default_factory=list)  # trusted only
    bp_flagged: list[dict] = field(default_factory=list)  # readings the trust check flagged
    bp_red_pairs: list[tuple[int, int]] = field(default_factory=list)  # pairs to test against red-flag floors
    other_flagged: list[dict] = field(default_factory=list)  # glucose/hr/steps flagged
    steps: int | None = None
    replies: int = 0
    social: bool = False
    symptoms: set[str] = field(default_factory=set)
    red_symptoms: list[str] = field(default_factory=list)  # the senior's own words
    unwell: bool = False
    taken: bool = False
    missed: bool = False
    double_dose: bool = False
    running_out: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    words: list[str] = field(default_factory=list)  # raw check-in text, for the GP brief
    psi: int | None = None
    rain_mm: float | None = None
    festival: str | None = None

    @property
    def sys(self) -> float | None:
        return mean(s for s, _ in self.bp) if self.bp else None

    @property
    def dia(self) -> float | None:
        return mean(d for _, d in self.bp) if self.bp else None


def build(store, senior: dict, upto: date, days: int = 60) -> dict[date, Day]:
    senior_id, region = senior["id"], senior.get("region")
    start = upto - timedelta(days=days - 1)
    out = {start + timedelta(i): Day(date=start + timedelta(i)) for i in range(days)}
    lo, hi = start.isoformat(), upto.isoformat()

    for r in store.list("reading", senior_id=senior_id, day_from=lo, day_to=hi):
        d = out.get(date.fromisoformat(r["time"][:10]))
        if d is None:
            continue
        trust = r.get("trust") or check(r)
        v = r.get("values") or {}
        if r["kind"] == "bp":
            d.bp_red_pairs.extend(red_flag_pairs({**r, "trust": trust}))
            if trust["ok"]:
                d.bp.append((int(v["systolic"]), int(v["diastolic"])))
            else:
                d.bp_flagged.append(r)
        elif r["kind"] == "steps":
            # A steps reading is the day's total so far: a watch syncs it through Apple Health or Health Connect
            # several times a day. Keep the largest, never the sum, or each sync would count the day again.
            if trust["ok"]:
                d.steps = max(d.steps or 0, int(v["count"]))
        elif not trust["ok"]:
            d.other_flagged.append(r)

    for c in store.list("checkin", senior_id=senior_id, day_from=lo, day_to=hi):
        d = out.get(date.fromisoformat(c["time"][:10]))
        if d is None:
            continue
        f = c.get("facts") or {}
        d.replies += 1
        d.words.append(c.get("raw_text", ""))
        d.social |= bool(f.get("social_contact"))
        for s in f.get("symptoms", []):
            d.symptoms.add(s["code"])
            if s.get("red_flag"):
                d.red_symptoms.append(s.get("words") or s["code"])
        d.unwell |= any(not s.get("red_flag") for s in f.get("symptoms", []))
        for dose in f.get("doses", []):
            if dose.get("taken"):
                d.taken = True
            else:
                d.missed = True
        d.double_dose |= bool(f.get("double_dose"))
        d.running_out += [m for m in f.get("running_out", []) if m not in d.running_out]
        d.questions += [q for q in f.get("questions", []) if q not in d.questions]
        # A BP the senior said (and the language layer was sure of) counts like a typed reading.
        for b in f.get("bp", []):
            if not b.get("needs_confirmation"):
                reading = {"kind": "bp", "values": {"systolic": b["systolic"], "diastolic": b["diastolic"]}}
                t = check(reading)
                d.bp_red_pairs.extend(red_flag_pairs({**reading, "trust": t}))
                if t["ok"]:
                    d.bp.append((b["systolic"], b["diastolic"]))

    for e in store.list("envday", day_from=lo, day_to=hi):
        d = out.get(date.fromisoformat(e["date"]))
        if d is not None and e.get("region") == region:
            d.psi = e.get("psi_24h")
            d.rain_mm = e.get("rainfall_mm")

    for d in out.values():
        d.festival = festival_on(d.date)
    return out
