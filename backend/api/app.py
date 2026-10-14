"""HTTP endpoints from the shared contract (contracts/README.md). Owner: Vibu.

    uvicorn backend.api.app:app --reload        # CARELOOP_SEED=demo seeds the demo on first start
"""
from __future__ import annotations

import json
import os
import random
import urllib.request
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Literal, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.engine import claim, run_day, todays_suggestions, trust_check
from backend.engine.baseline import bp as bp_baseline
from backend.engine.config import haze_band
from backend.engine.history import build
from backend.engine.ladder import SEVERITY, SGT, contacts_for
from backend.env.data import region_for_postal
from backend import healthsync
from backend.healthsync.ingest import recent as healthsync_recent
from backend.language import describe as model_chain
from backend.language import understand, write
from backend.language.facts import Facts

from . import demo
from .store import Store

VERSION = "0.1.0"

app = FastAPI(title="CareLoop SG", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = Store()
if os.environ.get("CARELOOP_SEED") == "demo" and not store.list("senior"):
    demo.seed(store)


def use_store(s: Store) -> None:
    """Tests point the app at their own store."""
    global store
    store = s


def today() -> date:
    return demo.today(store)


def now() -> datetime:
    t = today()
    real = datetime.now(SGT)
    return real if real.date() == t else datetime.combine(t, real.time(), SGT)


def senior_or_404(sid: str) -> dict:
    s = store.get("senior", sid)
    if s is None:
        raise HTTPException(404, f"no senior {sid}")
    return s


# --- requests ------------------------------------------------------------------------------

Lang = Literal["en", "en-SG", "zh"]


class CheckInIn(BaseModel):
    senior_id: str
    text: str = Field(min_length=1, max_length=2000)
    language: Optional[Lang] = None
    source: Literal["voice", "typed", "button"] = "typed"
    time: Optional[datetime] = None


class ReadingIn(BaseModel):
    senior_id: str
    kind: Literal["bp", "hr", "steps", "sleep", "glucose"]
    values: dict
    source: Literal["cuff", "watch", "voice"] = "cuff"
    confidence: float = 1.0
    time: Optional[datetime] = None


class ClaimIn(BaseModel):
    contact_id: str
    choice: str


class Consent(BaseModel):
    family_sees: Literal["nothing", "digest", "readings"] = "digest"
    share_words: bool = False
    share_activity: bool = True


class PairCodeIn(BaseModel):
    contact_name: str
    role: Literal["family", "aac"] = "family"
    language: Lang = "en"
    senior_name: str = ""
    home_postal: str = Field(default="560000", pattern=r"^\d{6}$")
    worker_id: Optional[str] = None


class PairIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    language: Lang = "en"
    consent: Consent = Consent()


class ResponseIn(BaseModel):
    response: Literal["not_for_me", "going"]


class Programme(BaseModel):
    title: str
    title_zh: Optional[str] = None
    weekdays: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]]
    time: str
    tags: list[str] = []
    indoor: bool = True
    free: bool = True


# --- everyone ------------------------------------------------------------------------------

@app.get("/meta")
def meta():
    return {"version": VERSION, **model_chain(), "today": today().isoformat(),
            "data_sources": {"psi": "NEA 24-hour PSI via data.gov.sg", "rain": "NEA rainfall via data.gov.sg",
                             "aac": "MOH Eldercare Services via data.gov.sg", "cc": "PA Community Clubs via data.gov.sg",
                             "people": "synthetic"},
            "thresholds": "PLACEHOLDER until clinical sign-off"}


# --- senior app ----------------------------------------------------------------------------

@app.post("/checkin")
def post_checkin(body: CheckInIn):
    senior = senior_or_404(body.senior_id)
    lang = body.language or senior["language"]
    t = body.time or now()
    facts = understand(body.text, lang)
    cid = f"ck-{body.senior_id}-{t.strftime('%Y%m%d%H%M%S')}-{random.randrange(10**6):06d}"
    store.put("checkin", {"id": cid, "senior_id": body.senior_id, "time": t.isoformat(), "source": body.source,
                          "raw_text": body.text, "language": lang, "facts": facts.to_dict()})
    before = set((store.get("decision", f"dec-{body.senior_id}-{t.date()}") or {}).get("message_ids", []))
    decision = run_day(store, body.senior_id, t.date(), now=t)
    new = [store.get("message", m) for m in decision["message_ids"] if m not in before]
    reply = next((m for m in new if m and m["to"] == "senior"), None)
    return {"checkin_id": cid, "facts": facts.to_dict(), "message": reply, "rung": decision["rung"]}


@app.post("/reading")
def post_reading(body: ReadingIn):
    senior_or_404(body.senior_id)
    t = body.time or now()
    r = {"id": f"rd-{body.senior_id}-{t.strftime('%Y%m%d%H%M%S')}-{random.randrange(10**6):06d}", "senior_id": body.senior_id,
         "time": t.isoformat(), "kind": body.kind, "values": body.values, "source": body.source, "confidence": body.confidence}
    r["trust"] = trust_check(r)
    store.put("reading", r)
    before = set((store.get("decision", f"dec-{body.senior_id}-{t.date()}") or {}).get("message_ids", []))
    decision = run_day(store, body.senior_id, t.date(), now=t)
    new = [store.get("message", m) for m in decision["message_ids"] if m not in before]
    reply = next((m for m in new if m and m["to"] == "senior"), None)
    return {"reading": r, "rung": decision["rung"], "message": reply}


@app.get("/senior/{sid}/today")
def senior_today(sid: str):
    senior = senior_or_404(sid)
    t = today()
    d = build(store, senior, t, days=2)[t]
    checkins = store.list("checkin", senior_id=sid, day_from=t.isoformat(), day_to=t.isoformat())
    hh, mm = map(int, senior.get("usual_checkin_time", "08:00").split(":"))
    # A check-in that only says "took my pills" isn't the morning check-in.
    feel_logged = any(c["facts"].get("symptoms") or c["facts"].get("mood") or c["facts"].get("activities") for c in checkins)
    due = not feel_logged and now().hour * 60 + now().minute >= hh * 60 + mm - 30
    prompt = None
    if due:
        m = write("1", Facts(lang=senior["language"]), senior["language"], to="senior", context={"name": senior["name"]})
        prompt = {"to": "senior", "rung": "1", "language": m.language, "text": m.text, "from_template": m.from_template,
                  "guardrail": {"passed": m.guardrail.passed, "reasons": m.guardrail.reasons}, "model": m.model}
    band, en, zh = haze_band(d.psi)
    haze = {"psi": d.psi, "band": band, "text": zh if senior["language"] == "zh" else en} if en else None
    return {
        "senior": {"id": sid, "name": senior["name"], "language": senior["language"]},
        "date": t.isoformat(),
        "pills_taken": d.taken, "bp_logged": bool(d.bp or d.bp_flagged),
        "feel_logged": feel_logged,
        "checkin_due": due, "prompt": prompt, "haze": haze,
        "suggestions": todays_suggestions(store, senior, t, d),
    }


@app.get("/senior/{sid}/knows")
def knows(sid: str):
    s = senior_or_404(sid)
    zh = s["language"] == "zh"
    out = [{"id": f"condition:{c}", "kind": "condition", "text": (f"有{c}" if zh else f"Has {c}")} for c in s.get("conditions", [])]
    out += [{"id": f"medicine:{m['name']}", "kind": "medicine",
             "text": (f"吃 {m['name']}，{m.get('dose_text', '')}" if zh else f"Takes {m['name']}, {m.get('dose_text', '')}").rstrip(", ，")}
            for m in s.get("medicines", [])]
    out += [{"id": f"like:{l}", "kind": "like", "text": (f"喜欢{l}" if zh else f"Likes {l}")} for l in s.get("likes", [])]
    out.append({"id": "routine:checkin", "kind": "routine",
                "text": (f"通常在{s['usual_checkin_time']}左右问候" if zh else f"Usually checks in around {s['usual_checkin_time']}")})
    for c in store.list("contact", senior_id=sid):
        out.append({"id": f"contact:{c['id']}", "kind": "contact",
                    "text": (f"{c['name']}是联系人" if zh else f"{c['name']} is a contact")})
    for k in store.list("knows", senior_id=sid):
        out.append({"id": f"learned:{k['id']}", "kind": "other", "text": k["text"]})
    return out


@app.delete("/senior/{sid}/knows/{fact}", status_code=204)
def forget(sid: str, fact: str):
    s = senior_or_404(sid)
    kind, _, key = fact.partition(":")
    if kind == "condition":
        s["conditions"] = [c for c in s.get("conditions", []) if c != key]
    elif kind == "medicine":
        s["medicines"] = [m for m in s.get("medicines", []) if m["name"] != key]
    elif kind == "like":
        s["likes"] = [l for l in s.get("likes", []) if l != key]
    elif kind == "routine":
        s["usual_checkin_time"] = "08:00"
    elif kind == "contact":
        if not store.delete("contact", key):
            raise HTTPException(404, fact)
    elif kind == "learned":
        if not store.delete("knows", key):
            raise HTTPException(404, fact)
    else:
        raise HTTPException(404, fact)
    store.put("senior", s)
    return Response(status_code=204)


@app.post("/senior/{sid}/suggestions/{sug_id}/response")
def suggestion_response(sid: str, sug_id: str, body: ResponseIn):
    s = senior_or_404(sid)
    sug = store.get("suggestion", sug_id)
    if sug is None or sug["senior_id"] != sid:
        raise HTTPException(404, sug_id)
    sug["response"] = body.response
    store.put("suggestion", sug)
    if body.response == "not_for_me" and sug["place_id"] not in s["hidden_suggestions"]:
        s["hidden_suggestions"].append(sug["place_id"])  # remembered, not repeated next week
        store.put("senior", s)
    return sug


@app.post("/pair")
def pair(body: PairIn):
    pc = store.get("paircode", body.code)
    if pc is None or pc.get("used"):
        raise HTTPException(404, "unknown or used code")
    sid = pc["senior_id"]
    region = region_for_postal(pc["home_postal"])
    store.put("senior", {
        "id": sid, "name": pc["senior_name"] or "", "language": body.language, "home_postal": pc["home_postal"], "region": region,
        "path": pc["role"], "aac_id": None, "conditions": ["hypertension"], "medicines": [], "likes": [],
        "usual_checkin_time": "08:00", "consent": body.consent.model_dump(), "hidden_suggestions": [],
    })
    store.put("contact", {"id": pc["contact_id"], "senior_id": sid, "role": pc["role"], "primary": True,
                          "name": pc["contact_name"], "language": pc["language"], "worker_id": pc.get("worker_id")})
    store.put("paircode", {**pc, "used": True})
    return {"senior_id": sid, "contact_name": pc["contact_name"], "contact_id": pc["contact_id"]}


# --- caregiver app -------------------------------------------------------------------------

@app.post("/care/pair-code")
def pair_code(body: PairCodeIn):
    """The caregiver app makes a code; the senior app redeems it at POST /pair."""
    for _ in range(20):
        code = f"{random.randrange(10**6):06d}"
        if store.get("paircode", code) is None:
            break
    n = random.randrange(10**6)
    pc = {"id": code, "senior_id": f"sen-{n:06d}", "contact_id": f"con-{n:06d}", "contact_name": body.contact_name,
          "role": body.role, "language": body.language, "senior_name": body.senior_name, "home_postal": body.home_postal,
          "worker_id": body.worker_id, "used": False}
    store.put("paircode", pc)
    return {"code": code, "senior_id": pc["senior_id"], "contact_id": pc["contact_id"]}


def _week(sid: str, senior: dict, end: date) -> dict:
    """The numbers behind the weekly digest. The words are written by write() from these."""
    start = end - timedelta(6)
    days = build(store, senior, end, days=60)
    week = [days[start + timedelta(i)] for i in range(7)]
    sys_ = [x.sys for x in week if x.sys is not None]
    dia = [x.dia for x in week if x.dia is not None]
    decisions = store.list("decision", senior_id=sid, day_from=start.isoformat(), day_to=end.isoformat())
    worst = max((d["rung"] for d in decisions), key=SEVERITY.get, default="0")
    sees = (senior.get("consent") or {}).get("family_sees", "digest")
    bpb = bp_baseline(days, end)
    return {
        "week_start": start.isoformat(), "week_end": end.isoformat(),
        "headline": "quiet" if worst in ("0", "1", "2") else ("worth a look" if worst == "3" else "needs you"),
        "readings_days": len(sys_),
        "mean_systolic": round(mean(sys_), 1) if sys_ and sees == "readings" else None,
        "mean_diastolic": round(mean(dia), 1) if dia and sees == "readings" else None,
        "baseline": {"systolic": bpb["systolic"], "diastolic": bpb["diastolic"]} if sees == "readings" else None,
        "pills_taken_days": sum(x.taken for x in week), "missed_days": sum(x.missed for x in week),
        "checkin_days": sum(x.replies > 0 for x in week), "social_days": sum(x.social for x in week),
        "worth_raising": sorted({d["reason"] for d in decisions if d["rung"] == "3"}),
    }


def _status(sid: str, t: date) -> str:
    d = store.get("decision", f"dec-{sid}-{t}") or {}
    open_ho = [h for h in store.list("handover", senior_id=sid) if h["status"] == "open"]
    if d.get("rung") == "R":
        return "red_flag"
    if open_ho:
        return "handover"
    return "quiet"


@app.get("/care/family/{contact_id}")
def family_view(contact_id: str):
    c = store.get("contact", contact_id)
    if c is None or c["role"] != "family":
        raise HTTPException(404, contact_id)
    senior = senior_or_404(c["senior_id"])
    sees = (senior.get("consent") or {}).get("family_sees", "digest")
    t = today()
    handovers = [h for h in store.list("handover", senior_id=senior["id"])
                 if h["status"] == "open" or (t - date.fromisoformat(h["opened_at"][:10])).days <= 14]
    red = [m for m in store.list("message", senior_id=senior["id"], day_from=(t - timedelta(2)).isoformat())
           if m["rung"] == "R" and m["to"] == "family"]
    others = [o for o in contacts_for(store, senior) if o["id"] != contact_id]
    return {
        "contact": c, "senior": {"id": senior["id"], "name": senior["name"], "language": senior["language"]},
        "family_sees": sees, "today": t.isoformat(), "status": _status(senior["id"], t),
        "digest": _week(senior["id"], senior, t) if sees != "nothing" else None,
        "handovers": [{**h, "claimed_by_name": (store.get("contact", h["claimed_by"]) or {}).get("name") if h["claimed_by"] else None}
                      for h in reversed(handovers)],
        "red_flags": red, "other_contacts": [{"id": o["id"], "name": o["name"]} for o in others],
    }


@app.get("/care/aac/{worker_id}/caseload")
def caseload(worker_id: str):
    """Every enrolled senior, sorted by who needs a look today. Quiet rows for quiet seniors."""
    t = today()
    rows = []
    for c in store.list("contact"):
        if c.get("role") != "aac" or c.get("worker_id") != worker_id:
            continue
        s = store.get("senior", c["senior_id"])
        if s is None:
            continue
        d = store.get("decision", f"dec-{s['id']}-{t}") or {}
        status = _status(s["id"], t)
        open_ho = next((h for h in store.list("handover", senior_id=s["id"]) if h["status"] == "open"), None)
        last_reply = max((x["time"] for x in store.list("checkin", senior_id=s["id"], day_from=(t - timedelta(14)).isoformat())), default=None)
        rows.append({
            "senior": {"id": s["id"], "name": s["name"], "language": s["language"]}, "contact_id": c["id"], "status": status,
            "today": {"rung": d.get("rung"), "reason": d.get("reason")}, "handover": open_ho, "last_reply": last_reply,
        })
    order = {"red_flag": 0, "handover": 1, "quiet": 2}
    rows.sort(key=lambda r: (order[r["status"]], r["senior"]["name"]))
    return {"worker_id": worker_id, "today": t.isoformat(), "seniors": rows}


@app.post("/handover/{hid}/claim")
def claim_handover(hid: str, body: ClaimIn):
    try:
        return claim(store, hid, body.contact_id, body.choice, now=now())
    except KeyError:
        raise HTTPException(404, hid)
    except PermissionError:
        raise HTTPException(403, "not a contact for this senior")
    except ValueError as e:
        raise HTTPException(400, str(e))


def _programmes(aac_id: str) -> list[dict]:
    return [p for p in store.list("programme") if p["place_id"] == aac_id]


@app.get("/aac/{aac_id}/programmes")
def get_programmes(aac_id: str):
    _refresh_feed(aac_id)
    return _programmes(aac_id)


@app.put("/aac/{aac_id}/programmes")
def put_programmes(aac_id: str, programmes: list[Programme] = Body(...)):
    """AAC staff enter their weekly timetable once; it feeds every linked senior's suggestions."""
    for p in _programmes(aac_id):
        store.delete("programme", p["id"])
    out = []
    for i, p in enumerate(programmes):
        doc = {"id": f"prog-{aac_id}-{i}", "place_id": aac_id, **p.model_dump(), "sample": False}
        store.put("programme", doc)
        out.append(doc)
    return out


# --- Timetable import (added: Nathan, needs team OK) ---------------------------------------------
# Centres already keep a calendar or a spreadsheet. Import it instead of retyping it; a calendar link is
# pulled again once a day, so a change in the centre's calendar reaches seniors' suggestions on its own.

FEED_REFRESH = timedelta(hours=24)


class TimetableIn(BaseModel):
    text: Optional[str] = Field(default=None, max_length=200_000)
    url: Optional[str] = Field(default=None, max_length=500)
    save: bool = False


def _fetch(url: str) -> str:
    url = "https://" + url[len("webcal://"):] if url.startswith("webcal://") else url
    if not url.startswith(("https://", "http://")):
        raise HTTPException(400, "a calendar link starts with https://")
    req = urllib.request.Request(url, headers={"User-Agent": "CareLoop-SG timetable import"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read(1_000_000).decode("utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(502, f"could not fetch the calendar: {e}")


def _feed(aac_id: str) -> dict | None:
    v = store.setting(f"programme_feed:{aac_id}")
    return json.loads(v) if v else None


def _refresh_feed(aac_id: str) -> None:
    """Pull a saved calendar link again if it's a day old. A failed pull keeps the last good timetable."""
    feed = _feed(aac_id)
    if not feed or datetime.now(SGT) - datetime.fromisoformat(feed["pulled_at"]) < FEED_REFRESH:
        return
    from backend.reports.timetable import parse

    try:
        progs, warnings = parse(_fetch(feed["url"]), today=today())
        if progs:
            put_programmes(aac_id, [Programme(**p) for p in progs])
        feed.update(pulled_at=datetime.now(SGT).isoformat(), error=None, count=len(progs), warnings=warnings)
    except HTTPException as e:
        feed.update(pulled_at=datetime.now(SGT).isoformat(), error=e.detail)
    store.set_setting(f"programme_feed:{aac_id}", json.dumps(feed))


@app.post("/aac/{aac_id}/programmes/import")
def import_programmes(aac_id: str, body: TimetableIn):
    """Read a .ics calendar or a .csv timetable (pasted, uploaded or a link). With save=false it only shows what
    would be imported, so staff can check the guessed tags first; save=true replaces the timetable."""
    from backend.reports.timetable import parse

    if not body.text and not body.url:
        raise HTTPException(400, "send the file's text or a calendar link")
    progs, warnings = parse(body.text if body.text else _fetch(body.url), today=today())
    saved = []
    if body.save and progs:
        saved = put_programmes(aac_id, [Programme(**p) for p in progs])
        if body.url:
            store.set_setting(f"programme_feed:{aac_id}", json.dumps(
                {"url": body.url, "pulled_at": datetime.now(SGT).isoformat(), "error": None, "count": len(progs), "warnings": warnings}))
    return {"programmes": saved or progs, "warnings": warnings, "saved": bool(saved), "feed": _feed(aac_id)}


@app.get("/aac/{aac_id}/programmes/feed")
def programme_feed(aac_id: str):
    return _feed(aac_id)


@app.delete("/aac/{aac_id}/programmes/feed")
def stop_programme_feed(aac_id: str):
    store.set_setting(f"programme_feed:{aac_id}", "")
    return None


@app.get("/senior/{sid}/brief.json")
def brief_data(sid: str, days: int = 90):
    """Everything the one-page GP brief needs. Every line traces to the decision log."""
    senior = senior_or_404(sid)
    t = today()
    hist = build(store, senior, t, days=days)
    bpb = bp_baseline(hist, t)
    decisions = store.list("decision", senior_id=sid, day_from=(t - timedelta(days - 1)).isoformat(), day_to=t.isoformat())
    words = []
    for c in store.list("checkin", senior_id=sid, day_from=(t - timedelta(days - 1)).isoformat()):
        if c["facts"].get("symptoms") or c["facts"].get("questions"):
            words.append({"date": c["time"][:10], "said": c["raw_text"], "language": c["language"],
                          "symptoms": [s["code"] for s in c["facts"]["symptoms"]], "questions": c["facts"].get("questions", [])})
    aac = None
    if senior.get("aac_id"):
        from backend.env.places import place

        p = place(senior["aac_id"])
        aac = {"id": senior["aac_id"], "name": p["name"] if p else None,
               "going": [s["place"] for s in store.list("suggestion", senior_id=sid) if s.get("response") == "going"]}
    return {
        "senior": {"id": sid, "name": senior["name"], "conditions": senior.get("conditions", []), "medicines": senior.get("medicines", [])},
        "period": {"from": (t - timedelta(days - 1)).isoformat(), "to": t.isoformat()},
        "baseline": bpb,
        "bp_daily": [{"date": d.date.isoformat(), "systolic": round(d.sys, 1) if d.sys else None, "diastolic": round(d.dia, 1) if d.dia else None}
                     for d in hist.values()],
        "adherence": {"taken_days": sum(d.taken for d in hist.values()), "missed_days": sum(d.missed for d in hist.values()),
                      "reported_days": sum(d.taken or d.missed for d in hist.values())},
        "events": [{"date": d["date"], "rung": d["rung"], "rule_id": d["rule_id"], "reason": d["reason"], "decision_id": d["id"]}
                   for d in decisions if d["rung"] in ("3", "4", "R")],
        "in_their_words": words, "aac": aac,
        # From the care notes the family and centre keep (added: Nathan): their questions, and the next visit.
        "family_questions": [q["text"] for q in (store.get("carenotes", f"notes-{sid}") or {}).get("questions", []) if not q.get("asked")],
        "next_appointment": next((a for a in sorted((store.get("carenotes", f"notes-{sid}") or {}).get("appointments", []), key=lambda a: a["date"])
                                  if a["date"] >= t.isoformat()), None),
        "note": "Generated from the CareLoop decision log. Not connected to any clinic system. Synthetic data in the demo.",
    }


@app.get("/senior/{sid}/log")
def decision_log(sid: str, days: int = 14, contact: Optional[str] = None):
    """Every day's decision, rung 0 included, with that day's facts. Newest first. (added: Nathan, needs team OK)

    For the family timeline and the AAC befriending record. Pass `contact` when a family member asks: the
    senior's consent then applies. Red-flag days are always shown in full.
    - family_sees "nothing": only red-flag days carry a rung and reason.
    - family_sees "digest": no numbers (reasons are left out, since they quote readings; rule ids stay).
    - share_words false: no check-in words.
    AAC staff, and calls without `contact`, see everything (AAC consent is given at enrolment).
    """
    senior = senior_or_404(sid)
    days = max(1, min(days, 60))
    family = False
    if contact is not None:
        c = store.get("contact", contact)
        if c is None or c["senior_id"] != sid:
            raise HTTPException(403, "not a contact for this senior")
        family = c["role"] == "family"
    consent = senior.get("consent") or {}
    sees = consent.get("family_sees", "digest") if family else "readings"
    words_ok = consent.get("share_words", False) if family else True
    activity_ok = consent.get("share_activity", True) if family else True

    t = today()
    start = t - timedelta(days - 1)
    hist = build(store, senior, t, days=days)
    decisions = {d["date"]: d for d in store.list("decision", senior_id=sid, day_from=start.isoformat(), day_to=t.isoformat())}
    checkins: dict[str, list[dict]] = {}
    for c in store.list("checkin", senior_id=sid, day_from=start.isoformat(), day_to=t.isoformat()):
        checkins.setdefault(c["time"][:10], []).append(c)

    out = []
    for i in range(days):
        d = t - timedelta(i)
        key = d.isoformat()
        dec = decisions.get(key)
        h = hist.get(d)
        red = bool(dec and dec["rung"] == "R")
        hidden = sees == "nothing" and not red
        numbers = sees == "readings" or red
        out.append({
            "date": key,
            "rung": None if hidden or not dec else dec["rung"],
            "rule_id": None if hidden or not dec else dec["rule_id"],
            "reason": dec["reason"] if dec and numbers and not hidden else None,
            "decision_id": dec["id"] if dec and not hidden else None,
            "checkins": [{"time": c["time"], "raw_text": c["raw_text"], "language": c["language"]}
                         for c in sorted(checkins.get(key, []), key=lambda c: c["time"])] if words_ok and not hidden else [],
            "replied": bool(h and h.replies) if not hidden else None,
            "pills": (None if hidden or not h else ("taken" if h.taken else "missed" if h.missed else None)),
            "social": bool(h and h.social) if activity_ok and not hidden else None,
            "bp": ({"systolic": round(h.sys), "diastolic": round(h.dia)} if h and h.sys and h.dia and numbers and not hidden else None),
            "psi": h.psi if h else None, "rain_mm": h.rain_mm if h else None, "festival": h.festival if h else None,
        })
    return out


def _viewer(sid: str, contact: Optional[str]) -> tuple[dict, bool, dict]:
    """The senior, whether a family member is asking, and what they may see (consent applies to family only)."""
    senior = senior_or_404(sid)
    family = False
    if contact is not None:
        c = store.get("contact", contact)
        if c is None or c["senior_id"] != sid:
            raise HTTPException(403, "not a contact for this senior")
        family = c["role"] == "family"
    consent = senior.get("consent") or {}
    return senior, family, {
        "sees": consent.get("family_sees", "digest") if family else "readings",
        "activity": consent.get("share_activity", True) if family else True,
    }


@app.get("/senior/{sid}/insights")
def senior_insights(sid: str, days: int = 30, contact: Optional[str] = None):
    """Patterns in the senior's own data: trends, weekday patterns, simple comparisons. (added: Nathan, needs team OK)

    Plain statistics (backend/reports/insights.py), no model. For family, consent applies: "nothing" is 403
    (red flags reach them anyway), "digest" drops readings, share_activity false drops steps and contact.
    """
    from backend.reports.insights import insights

    senior, family, see = _viewer(sid, contact)
    if see["sees"] == "nothing":
        raise HTTPException(403, "the senior shares only red flags")
    return insights(store, senior, today(), days=days, numbers=see["sees"] == "readings", activity=see["activity"])


@app.get("/senior/{sid}/activities")
def senior_activities(sid: str, contact: Optional[str] = None):
    """Their own AAC's programmes, the nearest AACs and CCs (data.gov.sg), recent suggestions and answers,
    and whether today calls for indoor options. (added: Nathan, needs team OK)"""
    from backend.reports.activities import activities

    senior, family, see = _viewer(sid, contact)
    return activities(store, senior, today(), responses=see["activity"])


# --- care notes: what the family and centre keep together (added: Nathan, needs team OK) -----------------

class Appointment(BaseModel):
    id: str = Field(max_length=40)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: Optional[str] = Field(default=None, max_length=10)
    place: str = Field(default="", max_length=120)
    purpose: str = Field(default="", max_length=200)
    who_goes: Optional[str] = Field(default=None, max_length=60)
    notes_after: str = Field(default="", max_length=1000)


class Question(BaseModel):
    id: str = Field(max_length=40)
    text: str = Field(min_length=1, max_length=300)
    by: str = Field(default="", max_length=60)
    added: str = Field(default="", max_length=30)
    asked: bool = False
    answer: str = Field(default="", max_length=500)


class Task(BaseModel):
    id: str = Field(max_length=40)
    title: str = Field(min_length=1, max_length=200)
    due: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    owner: Optional[str] = Field(default=None, max_length=60)
    done: bool = False
    done_by: Optional[str] = Field(default=None, max_length=60)


class Emergency(BaseModel):
    allergies: str = Field(default="", max_length=300)
    gp_name: str = Field(default="", max_length=120)
    gp_phone: str = Field(default="", max_length=30)
    home_address: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=500)


class CareNotes(BaseModel):
    appointments: list[Appointment] = Field(default_factory=list, max_length=50)
    questions: list[Question] = Field(default_factory=list, max_length=50)
    tasks: list[Task] = Field(default_factory=list, max_length=100)
    emergency: Emergency = Field(default_factory=Emergency)


def _linked_contact(sid: str, contact: Optional[str]) -> dict:
    c = store.get("contact", contact) if contact else None
    if c is None or c["senior_id"] != sid:
        raise HTTPException(403, "not a contact for this senior")
    return c


@app.get("/senior/{sid}/care-notes")
def get_care_notes(sid: str, contact: Optional[str] = None):
    """Appointments, questions for the doctor, shared to-dos and the emergency card. Every linked contact
    sees and edits the same notes. Nothing here changes what the engine decides."""
    senior_or_404(sid)
    _linked_contact(sid, contact)
    doc = store.get("carenotes", f"notes-{sid}")
    return doc or {"id": f"notes-{sid}", "senior_id": sid, **CareNotes().model_dump(), "updated_by": None, "updated_at": None}


@app.put("/senior/{sid}/care-notes")
def put_care_notes(sid: str, body: CareNotes, contact: Optional[str] = None):
    senior_or_404(sid)
    c = _linked_contact(sid, contact)
    doc = {"id": f"notes-{sid}", "senior_id": sid, **body.model_dump(), "updated_by": c["name"], "updated_at": now().isoformat()}
    store.put("carenotes", doc)
    return doc


@app.get("/senior/{sid}/brief.pdf")
def brief_pdf(sid: str):
    try:
        from backend.reports import gp_brief_pdf  # Nathan
    except ImportError:
        raise HTTPException(501, "GP brief PDF is backend/reports (Nathan); data at /senior/{id}/brief.json")
    return Response(gp_brief_pdf(brief_data(sid)), media_type="application/pdf")


# --- Health apps on the senior's phone (added: Nathan, needs team OK) ------------------------------
# Apple Health (iPhone) and Health Connect (Android). A Fitbit and an OMRON cuff both write to them.
# A CareLoop app on the senior's phone would post the day's records here; in the demo, backend/healthsync/
# simulate.py stands in for that phone.

class HealthSyncIn(BaseModel):
    platform: Literal["health_connect", "healthkit"]
    records: list[dict] = Field(max_length=5000)


def _after_sync(sid: str, out: dict, t: datetime) -> dict:
    """Run today again if the sync touched it, as after any new reading (a synced 186/112 is a red flag)."""
    rung, reply = None, None
    if t.date().isoformat() in out["days"]:
        before = set((store.get("decision", f"dec-{sid}-{t.date()}") or {}).get("message_ids", []))
        decision = run_day(store, sid, t.date(), now=t)
        rung = decision["rung"]
        new = [store.get("message", m) for m in decision["message_ids"] if m not in before]
        reply = next((m for m in new if m and m["to"] == "senior"), None)
    kinds: dict[str, int] = {}
    for r in out["readings"]:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"status": out["status"], "imported": kinds, "days": out["days"], "skipped": out["skipped"], "rung": rung, "message": reply}


@app.post("/senior/{sid}/health-sync")
def post_health_sync(sid: str, body: HealthSyncIn):
    """Records from the senior's phone. Steps, resting heart rate and sleep become one reading a day (each sync
    replaces it); each BP measurement becomes a reading. Every reading passes the trust check."""
    senior_or_404(sid)
    t = now()
    return _after_sync(sid, healthsync.ingest(store, sid, body.platform, body.records, now=t), t)


@app.get("/senior/{sid}/health-sync")
def get_health_sync(sid: str, days: int = 7, contact: Optional[str] = None):
    """What's connected, when it last synced, and the last days of synced data. Consent applies to family."""
    senior, family, see = _viewer(sid, contact)
    if see["sees"] == "nothing":
        raise HTTPException(403, "the senior shares only red flags")
    st = healthsync.status(store, sid)
    rows = healthsync_recent(store, sid, today(), days=max(1, min(days, 30))) if st else []
    for r in rows:
        if not see["activity"]:
            r.update(steps=None, resting_hr=None, sleep_hours=None)
        if see["sees"] != "readings":
            r["bp"] = []
    return {"connected": st is not None, "status": st, "days": rows, "shares_readings": see["sees"] == "readings",
            "shares_activity": see["activity"]}


# --- demo ----------------------------------------------------------------------------------

class DemoSyncIn(BaseModel):
    bp: Optional[tuple[int, int]] = None


@app.post("/demo/health-sync/{sid}")
def demo_health_sync(sid: str, body: Optional[DemoSyncIn] = None):
    """Stands in for the senior's phone syncing now: today's Fitbit records so far, and a cuff reading if given."""
    senior_or_404(sid)
    t = now()
    out = demo.phone_sync(store, sid, t, bp=body.bp if body else None)
    if out is None:
        raise HTTPException(409, "no phone is connected for this senior in the demo")
    return _after_sync(sid, out, t)


@app.post("/demo/advance")
def demo_advance(days: int = Body(1, embed=True, ge=1, le=60)):
    t = demo.advance(store, days)
    return {"today": t.isoformat()}


@app.post("/demo/reset")
def demo_reset():
    demo.seed(store)
    return {"today": today().isoformat()}
