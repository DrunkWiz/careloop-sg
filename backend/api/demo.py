"""Demo data and the demo clock. Synthetic people only, said plainly in the app.

seed(): two family-path seniors and three AAC-path seniors with 40 calm days ending on the demo
"today". advance(n): moves the clock n days; each new day gets scripted synthetic data and the
engine runs for every senior. Mr Tan's script is the video: two quiet weeks in which a BP drift
starts, rungs 1-3 try gently, and rung 4 hands over to his daughter. The red flag ("I'm fine lah"
at 186/112) is NOT scripted: it is said live into the senior app.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from backend.engine import run_day, trust_check
from backend.engine.ladder import SGT
from backend.env.data import envday, fetch_envday
from backend.language import understand
from backend.language.gateway import Chain

DEMO_TODAY = date(2026, 10, 13)
NO_MODEL = Chain([])

SENIORS = [
    # id, name, language, postal, region, path, aac_id, likes, base sys/dia, steps
    # Postal codes are made up (sector only matters, for the PSI region); AAC ids are real centres from places.json.
    ("tan", "Mr Tan", "en-SG", "560999", "central", "family", "aac-100", ["mahjong", "kopi"], (128, 80), 5200),
    ("wong", "Mdm Wong", "zh", "640999", "west", "family", "aac-002", ["karaoke", "singing"], (132, 82), 3800),
    ("yeo", "Mrs Yeo", "en", "730999", "west", "family", "aac-100", ["gardening", "kopi"], (130, 81), 4400),  # Kelvin's mother
    ("lee", "Mdm Lee", "en", "520999", "east", "aac", "aac-105", ["crafts", "chatting"], (135, 84), 3000),
    ("goh", "Mr Goh", "zh", "521999", "east", "aac", "aac-105", ["exercise", "walking"], (126, 78), 6100),
    ("ng", "Mr Ng", "en-SG", "529999", "east", "aac", "aac-105", ["kopi", "chatting"], (138, 86), 2600),
]
# Caregivers: the person, independent of any senior. One caregiver can look after several seniors.
CAREGIVERS = [
    # id, name, language, role, worker_id
    ("cg-weiling", "Wei Ling", "en", "family", None),
    ("cg-kelvin", "Kelvin", "en", "family", None),
    ("cg-jane", "Jane", "en", "family", None),  # Kelvin's sister
    ("cg-mei", "Mei", "zh", "family", None),
    ("cg-siti", "Siti", "en", "aac", "aac-siti"),
]
# Links: senior → [(contact_id, caregiver_id, primary)]
LINKS = {
    "tan": [("tan-weiling", "cg-weiling", True), ("tan-kelvin", "cg-kelvin", False)],
    "wong": [("wong-mei", "cg-mei", True)],
    # Kelvin looks after his mother Mrs Yeo (primary) and helps with Mr Tan (secondary).
    # Jane (Kelvin's sister) also helps with Mrs Yeo (secondary).
    "yeo": [("yeo-kelvin", "cg-kelvin", True), ("yeo-jane", "cg-jane", False)],
    "lee": [("aac-siti:lee", "cg-siti", True)],
    "goh": [("aac-siti:goh", "cg-siti", True)],
    "ng": [("aac-siti:ng", "cg-siti", True)],
}

TEXT = {
    "en": {"ok": "Feeling ok today.", "took": "Took my pills.", "social": "Went to the centre with friends.", "home": "Stayed home today."},
    "en-SG": {"ok": "Ok lah, today fine.", "took": "Eat medicine already.", "social": "Kopi with my kakis.", "home": "Stay home today lor."},
    "zh": {"ok": "今天还好。", "took": "我吃了药。", "social": "和朋友去了活动中心。", "home": "今天在家。"},
}


def today(store) -> date:
    v = store.setting("demo_today")
    return date.fromisoformat(v) if v else datetime.now(SGT).date()


def _day_data(store, sid: str, d: date, *, lang: str, base: tuple[int, int], steps: int, extra_sys: float = 0,
              text_kind: str | None = None, steps_mult: float = 1.0, psi: int = 45, region: str = "central") -> None:
    rng = random.Random(f"{sid}-{d}")
    t = lambda hhmm: f"{d.isoformat()}T{hhmm}:00+08:00"
    if rng.random() < 0.85:
        r = {"id": f"{sid}-bp-{d}", "senior_id": sid, "time": t("08:05"), "kind": "bp", "source": "synthetic", "confidence": 1,
             "values": {"systolic": round(rng.gauss(base[0] + extra_sys, 4)), "diastolic": round(rng.gauss(base[1] + extra_sys / 2, 3)),
                        "pulse": rng.randint(64, 82)}}
        store.put("reading", {**r, "trust": trust_check(r)})
    r = {"id": f"{sid}-steps-{d}", "senior_id": sid, "time": t("21:00"), "kind": "steps", "source": "synthetic", "confidence": 1,
         "values": {"count": max(0, round(rng.gauss(steps * steps_mult, steps * 0.1)))}}
    store.put("reading", {**r, "trust": trust_check(r)})
    for j, kind in enumerate([text_kind or ("social" if rng.random() < 0.35 else "ok"), "took"]):
        raw = TEXT[lang][kind] if kind in TEXT[lang] else kind
        facts = understand(raw, lang, gateway=NO_MODEL)
        store.put("checkin", {"id": f"{sid}-ck-{d}-{j}", "senior_id": sid, "time": t(f"0{8 + j}:30"), "source": "synthetic",
                              "raw_text": raw, "language": lang, "facts": facts.to_dict()})
    if store.get("envday", f"env-{d.isoformat()}-{region}") is None:
        store.put("envday", envday(d, region, psi=psi, rainfall_mm=0.0 if rng.random() < 0.8 else round(rng.uniform(1, 12), 1)))


def seed(store, *, days: int = 40) -> None:
    store.clear()
    store.set_setting("demo_today", DEMO_TODAY.isoformat())
    start = DEMO_TODAY - timedelta(days=days)
    consent = {"family_sees": "readings", "share_words": True, "share_activity": True}
    cg_map = {}
    for cg_id, name, lang, role, worker_id in CAREGIVERS:
        store.put("caregiver", {"id": cg_id, "name": name, "language": lang, "role": role, "worker_id": worker_id})
        cg_map[cg_id] = (name, lang, role, worker_id)
    for sid, name, lang, postal, region, path, aac, likes, base, steps in SENIORS:
        store.put("senior", {
            "id": sid, "name": name, "language": lang, "home_postal": postal, "region": region, "path": path, "aac_id": aac,
            "conditions": ["hypertension"],
            "medicines": [{"name": "amlodipine", "dose_text": "5 mg once a day", "schedule": ["morning"], "started": "2024-03-01", "for_bp": True}],
            "likes": likes, "usual_checkin_time": "08:00",
            "consent": consent, "hidden_suggestions": [],
        })
        for cid, cg_id, primary in LINKS[sid]:
            cg_name, cg_lang, cg_role, cg_worker = cg_map[cg_id]
            store.put("contact", {"id": cid, "caregiver_id": cg_id, "senior_id": sid, "role": cg_role, "primary": primary,
                                  "name": cg_name, "language": cg_lang, "worker_id": cg_worker, "consent": consent})

    # Mr Tan's weekly sibling rota: Wei Ling and Kelvin take turns.
    store.put("rota", {"id": "rota-tan", "senior_id": "tan", "mode": "weekly", "start_date": start.isoformat(),
                       "order": ["tan-weiling", "tan-kelvin"], "swaps": []})

    for sid, name, lang, postal, region, path, aac, likes, base, steps in SENIORS:
        for i in range(days):
            d = start + timedelta(i)
            _day_data(store, sid, d, lang=lang, base=base, steps=steps, region=region)
            run_day(store, sid, d, gateway=NO_MODEL)
        # Today's haze is real: the newest data.gov.sg fixture (PSI 115-165 on 13 Oct 2026).
        store.put("envday", fetch_envday(DEMO_TODAY, region))

    # Vent space: seed a few sample posts so the screen isn't empty.
    _seed_vent(store, DEMO_TODAY)


def _seed_vent(store, today: date) -> None:
    """5–6 anonymous vent posts, all within the last 7 days of the demo today."""
    now = datetime.combine(today, datetime.min.time(), SGT)
    posts = [
        ("Caregiver 042", "Third time this week Pa refused to take his pill, I'm so tired",
         now - timedelta(hours=2), 3),
        ("Caregiver 128", "Anyone else feel guilty for needing a break?",
         now - timedelta(hours=5), 7),
        ("Caregiver 077", "Mum said I don't care about her. I do everything for her. That hurt.",
         now - timedelta(days=1, hours=3), 5),
        ("Caregiver 214", "Finally got 6 hours of sleep last night. Small wins.",
         now - timedelta(days=2, hours=5), 12),
        ("Caregiver 091", "The doctor said her BP is improving. I was so relieved I cried.",
         now - timedelta(days=3, hours=2), 8),
        ("Caregiver 156", "Sometimes I wonder if I'm doing enough for him.",
         now - timedelta(days=5, hours=6), 4),
    ]
    for nick, text, when, hugs in posts:
        store.put("ventpost", {
            "id": f"vp-demo-{nick.split()[1]}",
            "nickname": nick,
            "text": text,
            "time": when.isoformat(),
            "hugs": hugs,
            "hidden": False,
        })


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
            _day_data(store, sid, t, lang=lang, base=base, steps=steps, region=region, **_script(sid, n))
        for sid in seniors:
            run_day(store, sid, t, gateway=gateway if gateway is not None else NO_MODEL)
    store.set_setting("demo_today", t.isoformat())
    return t
