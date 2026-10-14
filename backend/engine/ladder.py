"""run_day: one decision per senior per day, logged with its reason, then the messages it allows.

The rule table picks the rung (rules.py). This module applies consent and the AAC weekly cap,
writes the decision log, opens a handover at rung 4 / R, and asks the language layer for the
words. It is safe to re-run for the same day (every check-in does): the decision is recomputed
and only messages not yet sent for that rung go out.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from backend.language import write
from backend.language.facts import BP, Facts, Symptom
from backend.language.gateway import Chain

from backend.env.places import suggest

from . import baseline as base
from .config import T
from .history import Day, build
from .rules import Ctx, Outcome, evaluate

SEVERITY = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "R": 5}
SGT = timezone(timedelta(hours=8))

OPTIONS = {
    "family": [
        {"id": "polyclinic", "label": "Book a polyclinic slot"},
        {"id": "gp_note", "label": "Draft a note to the GP"},
        {"id": "call", "label": "Call them today"},
    ],
    "aac": [
        {"id": "home_visit", "label": "Suggest a home visit"},
        {"id": "call", "label": "Call them today"},
        {"id": "gp_note", "label": "Draft a note to the GP"},
    ],
    "red_flag": [
        {"id": "call_now", "label": "Call them now"},
        {"id": "995", "label": "Call 995 for them"},
    ],
    "double_dose": [
        {"id": "pharmacist", "label": "Call the pharmacist or GP"},
        {"id": "call", "label": "Call them today"},
    ],
}


def now_sgt() -> datetime:
    return datetime.now(SGT)


def decision_id(senior_id: str, day: date) -> str:
    return f"dec-{senior_id}-{day.isoformat()}"


def contacts_for(store, senior: dict) -> list[dict]:
    role = "aac" if senior.get("path") == "aac" else "family"
    cs = [c for c in store.list("contact", senior_id=senior["id"]) if c["role"] == role]
    return [c for c in cs if c.get("primary")] or cs


def run_day(store, senior_id: str, day: date, *, now: datetime | None = None, gateway=None) -> dict:
    senior = store.get("senior", senior_id)
    if senior is None:
        raise KeyError(senior_id)
    now = now or now_sgt()
    if now.date() != day:
        now = datetime.combine(day, datetime.min.time(), SGT).replace(hour=21)  # a past (or demo) day is logged at its own evening
    did = decision_id(senior_id, day)
    days = build(store, senior, day)

    handovers = store.list("handover", senior_id=senior_id)
    open_ho = next((h for h in reversed(handovers)
                    if h["status"] == "open" and h["decision_id"] != did and h["opened_at"][:10] <= day.isoformat()), None)
    recent = [x for x in store.list("decision", senior_id=senior_id, day_from=(day - timedelta(14)).isoformat(),
                                    day_to=(day - timedelta(1)).isoformat())]

    ctx = Ctx(senior=senior, today=day, days=days, open_handover=open_ho, recent_decisions=recent)
    out = evaluate(ctx)
    cooling: set[str] = set()
    held: Outcome | None = None
    while out.rung == "4" and _cooling_down(out, handovers, day, did):
        held = held or _cooldown(out, handovers, day, did)
        cooling.add(out.kind)
        out = evaluate(ctx, frozenset(cooling))  # look past it for any other problem
    if held is not None and SEVERITY[out.rung] < SEVERITY["3"]:
        out = held
    out = _aac_cap(senior, out, recent, day)
    if out.rule_id == "2.low_day":
        sugs = todays_suggestions(store, senior, day, days[day])
        out.inputs["place"] = sugs[0]["place"] if sugs else None
    audience, consent_note = _audience(senior, out)

    prev = store.get("decision", did)
    if prev and SEVERITY[prev["rung"]] > SEVERITY[out.rung] and prev["rung"] in ("R", "4"):
        # A red flag or handover earlier today stands for the rest of the day.
        return prev

    decision = {
        "id": did, "senior_id": senior_id, "date": day.isoformat(), "rung": out.rung, "rule_id": out.rule_id,
        "reason": out.reason + (f" ({consent_note})" if consent_note else ""), "inputs": _jsonable(out.inputs),
        "audience": audience, "message_ids": list(prev["message_ids"]) if prev else [],
        "handover_id": prev.get("handover_id") if prev else None, "created_at": now.isoformat(),
    }

    if out.rung == "R" or (out.rung == "4" and not decision["handover_id"]):
        ho = _handover(store, senior, out, days, day, did, recent, now)
        decision["handover_id"] = ho["id"]

    contacts = contacts_for(store, senior)
    sent = {(m["to"], m["rung"]) for m in (store.get("message", mid) for mid in decision["message_ids"]) if m}
    for to in audience:
        if (to, out.rung) in sent:
            continue
        targets = [None] if to == "senior" else contacts
        for c in targets:
            msg = _message(senior, out, days[day], to, c, contacts, now, did, gateway)
            if msg is not None:
                store.put("message", msg)
                decision["message_ids"].append(msg["id"])
    store.put("decision", decision)
    return decision


def todays_suggestions(store, senior: dict, day: date, d: Day | None = None) -> list[dict]:
    """The suggestions card for a day: made once, then kept (so a 'not for me' sticks)."""
    existing = store.list("suggestion", senior_id=senior["id"], day_from=day.isoformat(), day_to=day.isoformat())
    if existing:
        return [s for s in existing if s.get("response") != "not_for_me"]
    if d is None:
        d = build(store, senior, day, days=2)[day]
    act = T["activity"]
    wet = any(x is not None and x >= act["rain_mm"] for x in (d.rain_mm,))
    hazy = (d.psi or 0) > act["haze_psi_above"]
    progs = [p for p in store.list("programme") if p.get("place_id") == senior.get("aac_id")] or None
    sugs = suggest(senior, day, indoor_only=wet or hazy, programmes=progs)
    for s in sugs:
        store.put("suggestion", s)
    return sugs


def _cooling_down(out: Outcome, handovers: list[dict], day: date, did: str) -> bool:
    return _cooldown(out, handovers, day, did) is not out


def _cooldown(out: Outcome, handovers: list[dict], day: date, did: str) -> Outcome:
    """Once the family has the evidence for a problem, the same problem isn't handed over again for
    a while: it goes in the digest instead. Red flags are never held back."""
    if out.rung != "4":
        return out
    days = T["hand_over"]["same_kind_cooldown_days"]
    prior = [h for h in handovers if h["kind"] == out.kind and h["decision_id"] != did
             and 0 < (day - date.fromisoformat(h["opened_at"][:10])).days <= days]
    if not prior:
        return out
    h = prior[-1]
    picked = f"; they chose: {h['choice']}" if h.get("choice") else "; still waiting for a next step"
    return Outcome("3", "3.already_handed_over", f"still the case ({out.reason}), but already handed over on "
                   f"{h['opened_at'][:10]}{picked}", out.inputs)


def _aac_cap(senior: dict, out: Outcome, recent: list[dict], day: date) -> Outcome:
    """AAC staff carry many seniors: at most one non-urgent alert (a handover) per senior per week.
    Digest notes never reach AAC staff as alerts; they show as the senior's caseload row."""
    if senior.get("path") != "aac" or out.rung != "4":
        return out
    week = [x for x in recent if date.fromisoformat(x["date"]) > day - timedelta(7) and x["rung"] == "4"]
    if len(week) >= T["aac_non_urgent_per_week"]:
        return Outcome("0", "0.aac_weekly_cap", f"no action, because the AAC already had a non-urgent alert this week "
                       f"({week[-1]['date']}); held back: {out.rule_id}: {out.reason}", out.inputs)
    return out


def _audience(senior: dict, out: Outcome) -> tuple[list[str], str]:
    carer = "aac" if senior.get("path") == "aac" else "family"
    sees = (senior.get("consent") or {}).get("family_sees", "digest")
    if out.rung == "R":
        return ["senior", carer], ""  # red flags are always shared; the senior was told so at setup
    if out.rung == "4":
        if carer == "family" and sees == "nothing":
            return ["senior"], "the senior chose not to share with family, so CareLoop tells the senior"
        return [carer, "senior"], ""
    if out.rung == "3":
        if carer == "aac":
            return [], "AAC caseload row only, no alert"
        if sees == "nothing":
            return [], "not shared: the senior chose to share nothing with family"
        return [carer], ""
    if out.rung in ("1", "2"):
        return ["senior"], ""
    return [], ""


def _facts_for(day: Day, out: Outcome, lang) -> Facts:
    f = Facts(lang=lang)
    for w in day.red_symptoms:
        f.symptoms.append(Symptom(code="reported", words=w, red_flag=True))
    if out.rule_id.startswith("R.bp"):
        f.bp.append(BP(systolic=out.inputs["systolic"], diastolic=out.inputs["diastolic"]))
    return f


def _message(senior, out: Outcome, day: Day, to: str, contact: dict | None, contacts: list[dict], now, did, gateway) -> dict | None:
    lang = (contact or senior).get("language") or senior.get("language", "en")
    names = [c["name"] for c in contacts]
    joiner = "和" if lang == "zh" else " and "
    primary = (", ".join(names[:-1]) + joiner + names[-1]) if len(names) > 1 else (names[0] if names else None)
    ctx = {"name": senior.get("name"), "contact": primary, "psi": day.psi}
    if to != "senior":
        ctx["summary"] = out.reason[0].upper() + out.reason[1:] + "."
    if out.rung == "2" and out.rule_id == "2.low_day":
        ctx["place"] = (out.inputs.get("place") or None)
    if out.rung == "2" and out.rule_id == "2.refill":
        ctx["place"] = "collecting your medicine refill" if lang != "zh" else "去拿药"
    m = write(out.rung, _facts_for(day, out, senior.get("language", "en")), lang, to=to, context=ctx,
              gateway=gateway if gateway is not None else None)
    if not m.text:
        return None
    return {
        "id": f"msg-{did}-{out.rung}-{to}-{(contact or {}).get('id', 'senior')}",
        "senior_id": senior["id"], "decision_id": did, "to": to, "contact_id": (contact or {}).get("id"),
        "rung": out.rung, "language": m.language, "text": m.text, "from_template": m.from_template,
        "guardrail": {"passed": m.guardrail.passed, "reasons": m.guardrail.reasons}, "model": m.model,
        "time": now.isoformat(),
    }


def _handover(store, senior, out: Outcome, days: dict[date, Day], day: date, did: str, recent: list[dict], now) -> dict:
    sees = (senior.get("consent") or {}).get("family_sees", "digest")
    show_readings = senior.get("path") == "aac" or sees == "readings" or out.rung == "R"
    window = [days[day - timedelta(i)] for i in range(13, -1, -1) if day - timedelta(i) in days]
    bpb = base.bp(days, day)
    kind = out.kind or "red_flag"
    options = OPTIONS.get(kind) or OPTIONS["aac" if senior.get("path") == "aac" else "family"]
    ho = {
        "id": f"ho-{did}-R" if out.rung == "R" else f"ho-{did}", "senior_id": senior["id"], "decision_id": did, "opened_at": now.isoformat(), "kind": kind,
        "evidence": {
            "summary": out.reason,
            "bp_series": [{"date": x.date.isoformat(), "systolic": round(x.sys, 1) if x.sys else None,
                           "diastolic": round(x.dia, 1) if x.dia else None} for x in window] if show_readings else [],
            "baseline": {"systolic": bpb["systolic"], "diastolic": bpb["diastolic"]} if show_readings else None,
            "dates": [x.date.isoformat() for x in window if x.missed or x.unwell or (x.sys and x.sys > T["hand_over"]["drift_systolic_over"])],
            "tried": [{"date": r["date"], "rung": r["rung"], "what": r["reason"]} for r in recent if r["rung"] in ("1", "2", "3")],
        },
        "options": options, "status": "open", "claimed_by": None, "claimed_at": None, "choice": None,
    }
    store.put("handover", ho, day=day.isoformat())
    return ho


def claim(store, handover_id: str, contact_id: str, choice: str, now: datetime | None = None) -> dict:
    """First to tap claims it; the others see who did. A reply that isn't one of the options
    ("just handle it") claims nothing: CareLoop never decides on its own to contact anyone."""
    ho = store.get("handover", handover_id)
    if ho is None:
        raise KeyError(handover_id)
    if ho["status"] == "claimed":
        return ho
    if choice not in {o["id"] for o in ho["options"]}:
        raise ValueError(f"'{choice}' is not one of the options; the handover stays open")
    contact = store.get("contact", contact_id)
    if contact is None or contact["senior_id"] != ho["senior_id"]:
        raise PermissionError(contact_id)
    ho.update(status="claimed", claimed_by=contact_id, claimed_at=(now or now_sgt()).isoformat(), choice=choice)
    store.put("handover", ho, day=ho["opened_at"][:10])
    return ho


def _jsonable(v):
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    if isinstance(v, date):
        return v.isoformat()
    return v


__all__ = ["run_day", "claim", "decision_id", "Chain"]
