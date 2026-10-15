"""Demo data and the demo clock. Synthetic people only, said plainly in the app.

seed(): twelve seniors (five on the family path, seven on the AAC path, at two centres) with 40 calm days
ending on the demo "today". advance(n): moves the clock n days; each new day gets scripted synthetic data
and the engine runs for every senior. Mr Tan's script is the video: two quiet weeks in which a BP drift
starts, rungs 1-3 try gently, and rung 4 hands over to his daughter. The red flag ("I'm fine lah" at
186/112) is NOT scripted: it is said live into the senior app.

The other scripts, over the same fortnight:
- Mdm Kaur: all quiet. Her Fitbit and OMRON cuff sync through Apple Health.
- Encik Rahman: forgets his pill on Sundays (a weekday pattern). Fitbit through Health Connect.
- Mdm Chua: one odd reading, then a mild rise. She shares a weekly summary only, not her readings.
- Mr Lim: stops answering check-ins, but his Fitbit still syncs steps, so it isn't treated as no contact.
- Mr Chandran: a BP drift seen through his OMRON cuff, handed over to his centre.
- Mr Osman: no reply and no steps for days, no weather excuse: handed over to his centre.
Five seniors have a phone that syncs from Health Connect or Apple Health (DEVICES); for the others,
steps are synthetic phone-pedometer counts.
"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from backend.engine import run_day, trust_check
from backend.engine.ladder import SGT
from backend.env.data import envday, fetch_envday
from backend.env.places import sample_programmes
from backend.healthsync import ingest
from backend.healthsync.simulate import phone_day
from backend.language import understand
from backend.language.gateway import Chain

DEMO_TODAY = date(2026, 10, 13)
NO_MODEL = Chain([])

SENIORS = [
    # id, name, language, postal, region, path, aac_id, likes, base sys/dia, steps
    # Postal codes are made up (sector only matters, for the PSI region); AAC ids are real centres from places.json.
    ("tan", "Mr Tan", "en-SG", "560999", "central", "family", "aac-100", ["mahjong", "kopi"], (128, 80), 5200),
    ("wong", "Mdm Wong", "zh", "640999", "west", "family", "aac-002", ["karaoke", "singing"], (132, 82), 3800),
    ("lee", "Mdm Lee", "en", "520999", "east", "aac", "aac-105", ["crafts", "chatting"], (135, 84), 3000),
    ("goh", "Mr Goh", "zh", "521999", "east", "aac", "aac-105", ["exercise", "walking"], (126, 78), 6100),
    ("ng", "Mr Ng", "en-SG", "529999", "east", "aac", "aac-105", ["kopi", "chatting"], (138, 86), 2600),
    ("kaur", "Mdm Kaur", "en", "460999", "east", "family", "aac-105", ["walking", "gardening", "chatting"], (124, 76), 6800),
    ("rahman", "Encik Rahman", "en", "650999", "west", "family", "aac-002", ["kopi", "exercise"], (134, 84), 4200),
    ("chua", "Mdm Chua", "zh", "310999", "central", "family", "aac-100", ["karaoke", "mahjong"], (130, 80), 3500),
    ("lim", "Mr Lim", "en-SG", "522999", "east", "aac", "aac-105", ["walking", "kopi"], (130, 82), 5600),
    ("chandran", "Mr Chandran", "en", "523999", "east", "aac", "aac-105", ["exercise", "health"], (129, 80), 4800),
    ("yeo", "Mdm Yeo", "zh", "561999", "central", "aac", "aac-100", ["crafts", "singing"], (127, 79), 3300),
    ("osman", "Mr Osman", "en-SG", "562999", "central", "aac", "aac-100", ["mahjong", "kopi"], (133, 83), 2900),
]
CONTACTS = {
    # An AAC contact's id starts with its worker: "aac-siti:lee" is Siti's link to Mdm Lee.
    "tan": [("tan-weiling", "Wei Ling", "family", "en"), ("tan-kelvin", "Kelvin", "family", "en")],
    "wong": [("wong-mei", "Mei", "family", "zh")],
    "lee": [("aac-siti:lee", "Siti (AAC)", "aac", "en")],
    "goh": [("aac-siti:goh", "Siti (AAC)", "aac", "en")],
    "ng": [("aac-siti:ng", "Siti (AAC)", "aac", "en")],
    "kaur": [("kaur-priya", "Priya", "family", "en"), ("kaur-arjun", "Arjun", "family", "en")],
    "rahman": [("rahman-nur", "Nur", "family", "en"), ("rahman-maria", "Maria (helper)", "family", "en")],
    "chua": [("chua-junjie", "Jun Jie", "family", "en"), ("chua-huimin", "Hui Min", "family", "zh")],
    "lim": [("aac-siti:lim", "Siti (AAC)", "aac", "en")],
    "chandran": [("aac-siti:chandran", "Siti (AAC)", "aac", "en")],
    "yeo": [("aac-farid:yeo", "Farid (AAC)", "aac", "en")],
    "osman": [("aac-farid:osman", "Farid (AAC)", "aac", "en")],
}
AAC_WORKER = "aac-siti"
CONSENT = {  # everyone else shares readings, words and activity
    "chua": {"family_sees": "digest", "share_words": False, "share_activity": True},
    "kaur": {"family_sees": "readings", "share_words": False, "share_activity": True},
}
# The phone each senior's data syncs from: platform, apps writing to it, usual resting heart rate.
DEVICES = {
    "tan": ("health_connect", ("fitbit", "omron"), 68),
    "kaur": ("healthkit", ("fitbit", "omron"), 64),
    "rahman": ("health_connect", ("fitbit",), 72),
    "lim": ("health_connect", ("fitbit",), 70),
    "chandran": ("health_connect", ("fitbit", "omron"), 74),
}

# Medicines and conditions. Everyone else takes amlodipine only. Mr Chandran's Zanidip is a brand CareLoop's
# medicine notes don't list, to show it saying so instead of guessing.
_AMLO = ("amlodipine", "5 mg once a day", ["morning"], True)
MEDS = {
    "kaur": [("telmisartan", "40 mg once a day", ["morning"], True), ("atorvastatin", "20 mg once a day", ["night"], False)],
    "rahman": [("amlodipine", "10 mg once a day", ["morning"], True), ("metformin", "500 mg twice a day, with meals", ["morning", "evening"], False)],
    "chua": [("losartan", "50 mg once a day", ["morning"], True), ("aspirin (low dose)", "100 mg once a day, after food", ["morning"], False)],
    "lim": [("bisoprolol", "2.5 mg once a day", ["morning"], True), ("hydrochlorothiazide", "12.5 mg once a day", ["morning"], True)],
    "chandran": [_AMLO, ("Zanidip", "10 mg once a day", ["morning"], True)],
}
CONDITIONS = {"kaur": ["hypertension", "high cholesterol"], "rahman": ["hypertension", "type 2 diabetes"]}

TEXT = {
    "en": {"ok": "Feeling ok today.", "took": "Took my pills.", "social": "Went to the centre with friends.", "home": "Stayed home today.",
           "missed": "Didn't take my medicine today, forgot."},
    "en-SG": {"ok": "Ok lah, today fine.", "took": "Eat medicine already.", "social": "Kopi with my kakis.", "home": "Stay home today lor.",
              "missed": "Never eat my medicine today, forgot."},
    "zh": {"ok": "今天还好。", "took": "我吃了药。", "social": "和朋友去了活动中心。", "home": "今天在家。", "missed": "今天忘了吃药。"},
}


def today(store) -> date:
    v = store.setting("demo_today")
    return date.fromisoformat(v) if v else datetime.now(SGT).date()


def _phone(store, sid: str, d: date, *, steps: int | None, bp: list[tuple[str, int, int]], upto: datetime | None = None) -> dict:
    """The senior's phone syncs: Fitbit and OMRON records, through Health Connect or Apple Health."""
    platform, apps, hr = DEVICES[sid]
    rng = random.Random(f"phone-num-{sid}-{d}")
    records = phone_day(sid, d, platform=platform, apps=apps, steps=steps, resting_hr=hr + rng.randint(-3, 3),
                        sleep_hours=round(rng.uniform(5.6, 7.8), 1), bp=bp, upto=upto)
    return ingest(store, sid, platform, records, now=upto or datetime.combine(d, time(22, 30), SGT))


def _steps_plan(store, sid: str, d: date, steps: int | None = None) -> int:
    """The day's whole step total in the demo. Every sync of that day replays the same hourly blocks from it,
    so a second sync sends the same records, and the total only grows as the hours pass."""
    key = f"demo-steps-plan:{sid}:{d}"
    if steps is None:
        v = store.setting(key)
        steps = int(v) if v else next(s[9] for s in SENIORS if s[0] == sid)
    store.set_setting(key, str(steps))
    return steps


def phone_sync(store, sid: str, now: datetime, bp: tuple[int, int] | None = None) -> dict | None:
    """For the demo's "sync now": what the phone has for today so far, plus a cuff measurement if given."""
    if sid not in DEVICES:
        return None
    steps = _steps_plan(store, sid, now.date())
    cuff = [(now.strftime("%H:%M"), bp[0], bp[1])] if bp else []
    return _phone(store, sid, now.date(), steps=steps, bp=cuff, upto=now)


def _day_data(store, sid: str, d: date, *, lang: str, base: tuple[int, int], steps: int, extra_sys: float = 0,
              text_kind: str | None = None, steps_mult: float = 1.0, psi: int = 45, region: str = "central",
              silent: bool = False, no_steps: bool = False) -> None:
    # The random draws stay in the order they had before phones were added, so every day's numbers are unchanged.
    rng = random.Random(f"{sid}-{d}")
    t = lambda hhmm: f"{d.isoformat()}T{hhmm}:00+08:00"
    device = DEVICES.get(sid)
    cuff = bool(device and "omron" in device[1])
    bp = None
    if rng.random() < 0.85:
        bp = (round(rng.gauss(base[0] + extra_sys, 4)), round(rng.gauss(base[1] + extra_sys / 2, 3)), rng.randint(64, 82))
    count = max(0, round(rng.gauss(steps * steps_mult, steps * 0.1)))
    if silent:
        bp = None
    if bp and not cuff:
        r = {"id": f"{sid}-bp-{d}", "senior_id": sid, "time": t("08:05"), "kind": "bp", "source": "synthetic", "confidence": 1,
             "values": {"systolic": bp[0], "diastolic": bp[1], "pulse": bp[2]}}
        store.put("reading", {**r, "trust": trust_check(r)})
    if device:
        if not no_steps:
            _steps_plan(store, sid, d, count)
        _phone(store, sid, d, steps=None if no_steps else count, bp=[("08:05", bp[0], bp[1])] if bp and cuff else [])
    elif not no_steps:
        r = {"id": f"{sid}-steps-{d}", "senior_id": sid, "time": t("21:00"), "kind": "steps", "source": "synthetic", "confidence": 1,
             "values": {"count": count}}
        store.put("reading", {**r, "trust": trust_check(r)})
    kinds = [text_kind or ("social" if rng.random() < 0.35 else "ok"), "took"]
    if text_kind == "missed":
        kinds = ["missed"]
    for j, kind in enumerate([] if silent else kinds):
        raw = TEXT[lang][kind] if kind in TEXT[lang] else kind
        facts = understand(raw, lang, gateway=NO_MODEL)
        store.put("checkin", {"id": f"{sid}-ck-{d}-{j}", "senior_id": sid, "time": t(f"0{8 + j}:30"), "source": "synthetic",
                              "raw_text": raw, "language": lang, "facts": facts.to_dict()})
    if store.get("envday", f"env-{d.isoformat()}-{region}") is None:
        store.put("envday", envday(d, region, psi=psi, rainfall_mm=0.0 if rng.random() < 0.8 else round(rng.uniform(1, 12), 1)))


def _routine(sid: str, d: date) -> dict:
    """Habits that run through the whole history, not only the fortnight."""
    if sid == "rahman" and d.weekday() == 6:
        return {"text_kind": "missed"}  # forgets his pill on Sundays
    return {}


def seed(store, *, days: int = 40) -> None:
    store.clear()
    store.set_setting("demo_today", DEMO_TODAY.isoformat())
    start = DEMO_TODAY - timedelta(days=days)
    for sid, name, lang, postal, region, path, aac, likes, base, steps in SENIORS:
        store.put("senior", {
            "id": sid, "name": name, "language": lang, "home_postal": postal, "region": region, "path": path, "aac_id": aac,
            "conditions": CONDITIONS.get(sid, ["hypertension"]),
            "medicines": [{"name": n, "dose_text": dose, "schedule": when, "started": "2024-03-01", "for_bp": bp}
                          for n, dose, when, bp in MEDS.get(sid, [_AMLO])],
            "likes": likes, "usual_checkin_time": "08:00",
            "consent": CONSENT.get(sid, {"family_sees": "readings", "share_words": True, "share_activity": True}), "hidden_suggestions": [],
        })
        for cid, cname, role, clang in CONTACTS[sid]:
            store.put("contact", {"id": cid, "senior_id": sid, "role": role, "primary": True, "name": cname, "language": clang,
                                  "worker_id": cid.split(":")[0] if role == "aac" else None})
        for i in range(days):
            d = start + timedelta(i)
            _day_data(store, sid, d, lang=lang, base=base, steps=steps, region=region, **_routine(sid, d))
            run_day(store, sid, d, gateway=NO_MODEL)
        # Today's haze is real: the newest data.gov.sg fixture (PSI 115-165 on 13 Oct 2026).
        store.put("envday", fetch_envday(DEMO_TODAY, region))
    _seed_plans(store)


def _day(n: int) -> str:
    return (DEMO_TODAY + timedelta(n)).isoformat()


def _seed_plans(store) -> None:
    """What a family and a centre would have typed in by the demo: Mr Tan's care plan and the centre's timetable.
    Dates count from the demo start; the to-dos fall just after the video's fortnight (24 Oct).
    The clinic, doctor, phone number and address are made up."""
    store.put("carenotes", {
        "id": "notes-tan", "senior_id": "tan", "updated_by": "Wei Ling", "updated_at": f"{_day(-3)}T20:15:00+08:00",
        "appointments": [
            {"id": "ap-1", "date": _day(-11), "time": "10:00", "place": "Ang Mo Kio Family Clinic (demo)", "purpose": "BP review",
             "who_goes": "Wei Ling", "notes_after": "BP fine at the clinic. Same amlodipine dose. Keep measuring at home each morning."},
            {"id": "ap-2", "date": _day(16), "time": "09:30", "place": "Ang Mo Kio Family Clinic (demo)", "purpose": "BP review and medicine refill",
             "who_goes": "Kelvin", "notes_after": ""},
        ],
        "questions": [
            {"id": "q-1", "text": "His morning readings are higher than at the clinic. Which ones should we trust?", "by": "Wei Ling",
             "added": _day(-3), "asked": False, "answer": ""},
            {"id": "q-2", "text": "Is it fine for him to take his pill after kopi instead of before breakfast?", "by": "Kelvin",
             "added": _day(-2), "asked": False, "answer": ""},
            {"id": "q-3", "text": "Should he keep using the old BP monitor?", "by": "Wei Ling", "added": _day(-12), "asked": True,
             "answer": "Yes, but bring it to the next visit so the clinic can check it."},
        ],
        "tasks": [
            {"id": "t-1", "title": "Collect amlodipine refill from the clinic", "due": _day(14), "owner": "Kelvin", "done": False, "done_by": None},
            {"id": "t-2", "title": "Buy new AA batteries for the BP monitor", "due": _day(12), "owner": "Wei Ling", "done": False, "done_by": None},
            {"id": "t-3", "title": "Put the emergency card on the fridge", "due": None, "owner": None, "done": True, "done_by": "Wei Ling"},
        ],
        # Staying well: last done. The flu vaccine was a year ago, so it shows as due in the video.
        "prevention": {"flu": "2025-10-04", "pneumococcal": "2024-11-12", "covid": "2025-11-20", "kidney": "2026-04-02",
                       "healthier_sg": "2024-02-15"},
        "emergency": {"allergies": "Penicillin (rash)", "gp_name": "Dr Lim, Ang Mo Kio Family Clinic (demo)", "gp_phone": "6000 0000",
                      "home_address": "Blk 999 Ang Mo Kio Ave 9, #05-123 (demo address)",
                      "notes": "Lives alone on weekdays. Spare key with the neighbour at #05-125."},
    })
    # Mr Lee, Mr Goh and Mr Ng's centre has entered its timetable (the sample one), so it is no longer marked as a sample.
    for p in sample_programmes("aac-105"):
        store.put("programme", {**p, "sample": False})


def _script(sid: str, n: int) -> dict:
    """What day n after the demo start looks like for each senior."""
    if sid == "tan":
        # Day 2: one odd reading (rung 1 asks). Day 4: pills running low (rung 2 suggests a refill).
        # From day 5 a drift climbs for a week and holds: rung 3 notes it, rung 4 hands over.
        if n == 2:
            return {"extra_sys": 26}
        if n == 4:
            return {"text_kind": "Ok lah. Medicine almost finish already."}
        return {"extra_sys": 0 if n < 5 else min(24, (n - 4) * 4)}
    if sid == "ng":
        # Lives alone: from day 5, low movement and no social contact.
        return {"steps_mult": 0.3, "text_kind": "home"} if n >= 5 else {}
    if sid == "chua":
        # Day 3: one odd reading (rung 1 asks to re-measure). Days 7-10: a mild rise, noted but not handed over.
        return {"extra_sys": 24} if n == 3 else {"extra_sys": 9} if 7 <= n <= 10 else {}
    if sid == "lim":
        # From day 6 he stops answering, but his Fitbit keeps syncing his walks.
        return {"silent": True} if n >= 6 else {}
    if sid == "chandran":
        # From day 4 a drift, measured by his OMRON cuff and synced through Health Connect.
        return {"extra_sys": min(24, (n - 3) * 4)} if n >= 4 else {}
    if sid == "osman":
        # From day 5: no reply and no steps (he has no watch), on dry days: no weather excuse.
        return {"silent": True, "no_steps": True} if n >= 5 else {}
    return {}


def advance(store, days: int, *, gateway=None) -> date:
    t = today(store)
    seniors = {s["id"]: s for s in store.list("senior")}
    for _ in range(days):
        t += timedelta(1)
        n = (t - DEMO_TODAY).days
        for sid, name, lang, postal, region, path, aac, likes, base, steps in SENIORS:
            if sid not in seniors:
                continue
            _day_data(store, sid, t, lang=lang, base=base, steps=steps, region=region, **{**_routine(sid, t), **_script(sid, n)})
        for sid in seniors:
            run_day(store, sid, t, gateway=gateway if gateway is not None else NO_MODEL)
    store.set_setting("demo_today", t.isoformat())
    return t
