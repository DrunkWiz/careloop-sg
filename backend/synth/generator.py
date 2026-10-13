"""Synthetic personas with planted events. No real patient data anywhere.

A persona is 90 days of BP readings, steps, check-in replies in their own language, and
weather, plus a list of the events planted in it with their dates and what CareLoop should do:
  expect "R"     a red flag: must be rung R that very day
  expect "4"     a real problem: should be handed over within the event window (+7 days)
  expect "none"  something that looks like a problem but isn't: a handover here is a false alarm
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

PHRASES = {
    "en": {
        "ok": ["Feeling ok today.", "Good morning, all fine.", "Slept well, feeling good.", "Not bad today."],
        "took": ["Took my pills.", "Taken my morning tablet."],
        "forgot": ["Forgot to take my pills this morning.", "I didn't take my medicine today."],
        "social": ["Went to the community centre with friends.", "Met my neighbours for coffee."],
        "mahjong": ["Played mahjong the whole day at my friend's flat.", "Mahjong all afternoon with friends."],
        "unwell": ["Not feeling well today, a bit dizzy.", "Feeling unwell, very tired."],
        "home": ["Stayed home today.", "Just rested at home."],
        "rain": ["Raining so stayed in.", "Too wet to go out."],
        "red_symptom": ["I'm fine, just some chest pain since morning.", "My face feels like it's drooping on one side."],
        "fine_high": ["I'm fine, BP {s}/{d} this morning."],
    },
    "en-SG": {
        "ok": ["Ok lah, today fine.", "Morning! All good one.", "Can lah, feeling ok.", "Shiok, slept well."],
        "took": ["Eat medicine already.", "Took already lah."],
        "forgot": ["Aiyo forgot to eat my medicine.", "Never eat medicine today, forgot."],
        "social": ["Go CC with my kakis.", "Kopi with neighbours this morning."],
        "mahjong": ["Play mahjong whole day lah.", "Mahjong whole afternoon with my kakis."],
        "unwell": ["Not feeling well leh, a bit giddy.", "Feeling unwell lah, no energy."],
        "home": ["Stay home today lor.", "Never go out today."],
        "rain": ["Rain so heavy, stay home lor.", "Raining, lazy to go out."],
        "red_symptom": ["I'm fine lah, just chest pain a bit.", "Almost pengsan just now."],
        "fine_high": ["I'm fine lah, BP {s}/{d} this morning."],
    },
    "zh": {
        "ok": ["今天还好。", "早上好，一切都好。", "睡得好，感觉不错。"],
        "took": ["我吃了药。", "早上的药吃过了。"],
        "forgot": ["今天忘记吃药了。", "早上没吃药。"],
        "social": ["和朋友去了活动中心。", "跟邻居喝咖啡。"],
        "mahjong": ["今天去朋友家打麻将，打了一整天。", "下午打麻将。"],
        "unwell": ["今天不太舒服，有点头晕。", "身体不舒服，很累。"],
        "home": ["今天在家。", "今天没出门。"],
        "rain": ["下大雨，在家。", "下雨没出门。"],
        "red_symptom": ["我没事，就是胸口痛。", "早上差点晕倒。"],
        "fine_high": ["我没事，血压{s}/{d}。"],
    },
}

NAMES = ["Mr Tan", "Mdm Lim", "Mr Goh", "Mdm Wong", "Mr Ng", "Mdm Lee", "Mr Chua", "Mdm Teo", "Mr Ong", "Mdm Koh",
         "Mr Yeo", "Mdm Chan", "Mr Ho", "Mdm Sim", "Mr Low", "Mdm Toh"]
LIKES = [["mahjong", "kopi"], ["karaoke", "singing"], ["exercise", "walking"], ["crafts"], ["health talks", "learning"], ["chatting", "food"]]
REGIONS = [("560123", "central"), ("640456", "west"), ("520789", "east"), ("730321", "north"), ("150654", "south")]


@dataclass
class Event:
    kind: str
    start: date
    end: date
    expect: str  # "R" | "4" | "none"
    note: str = ""


@dataclass
class Persona:
    senior: dict
    contacts: list[dict]
    readings: list[dict] = field(default_factory=list)
    checkins: list[dict] = field(default_factory=list)  # raw text only; understood at load time
    env: list[dict] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    start: date = date(2026, 7, 15)
    days: int = 90

    def to_json(self) -> dict:
        return {
            "senior": self.senior, "contacts": self.contacts, "readings": self.readings, "checkins": self.checkins,
            "env": self.env, "start": self.start.isoformat(), "days": self.days,
            "events": [{"kind": e.kind, "start": e.start.isoformat(), "end": e.end.isoformat(), "expect": e.expect, "note": e.note}
                       for e in self.events],
        }


def _t(d: date, hhmm: str) -> str:
    return f"{d.isoformat()}T{hhmm}:00+08:00"


def make_persona(rng: random.Random, idx: int, *, prefix: str, start: date | None = None, path: str | None = None,
                 lang: str | None = None, plan: list[str] | None = None, days: int = 90) -> Persona:
    lang = lang or rng.choice(["en", "en-SG", "zh"])
    path = path or ("aac" if rng.random() < 0.3 else "family")
    postal, region = rng.choice(REGIONS)
    sid = f"{prefix}{idx:02d}"
    senior = {
        "id": sid, "name": NAMES[idx % len(NAMES)], "language": lang, "home_postal": postal, "region": region, "path": path,
        "aac_id": f"aac-{rng.randrange(61):03d}" if path == "aac" or rng.random() < 0.5 else None,
        "conditions": ["hypertension"],
        "medicines": [{"name": "amlodipine", "dose_text": "5 mg once a day", "schedule": ["morning"], "started": "2024-01-01", "for_bp": True}],
        "likes": rng.choice(LIKES), "usual_checkin_time": rng.choice(["07:30", "08:00", "09:30"]),
        "consent": {"family_sees": rng.choice(["digest", "readings", "readings"]), "share_words": rng.random() < 0.5, "share_activity": True},
        "hidden_suggestions": [],
    }
    contacts = [{"id": f"{sid}-c1", "senior_id": sid, "role": path, "primary": True,
                 "name": "AAC befriender" if path == "aac" else "Daughter", "language": "en"}]
    if path == "family" and rng.random() < 0.4:
        contacts.append({"id": f"{sid}-c2", "senior_id": sid, "role": "family", "primary": True, "name": "Son", "language": "en"})

    start = start or date(2026, 7, 15)
    p = Persona(senior=senior, contacts=contacts, start=start, days=days)
    base_sys, base_dia = rng.randint(122, 138), rng.randint(74, 86)
    base_steps = rng.randint(2500, 7000)
    plan = plan if plan is not None else rng.sample(
        ["drift", "red_bp", "red_symptom", "missed_run", "haze_week", "rainy_week", "mahjong_days", "phone_home", "unwell_run", "isolation"], k=4)
    if start <= date(2026, 2, 17) < start + timedelta(days) and "cny_spike" not in plan:
        plan = plan + ["cny_spike"]

    # Per-day modifiers, filled by events.
    sys_add = [0.0] * days
    steps_mult = [1.0] * days
    psi = [rng.randint(25, 60)] * days
    rain = [0.0 if rng.random() < 0.75 else round(rng.uniform(0.5, 4), 1) for _ in range(days)]
    text_kind: list[str | None] = [None] * days
    missed = [rng.random() < 0.03 for _ in range(days)]
    no_phone = [False] * days
    social = [rng.random() < 0.35 for _ in range(days)]
    forced_bp: dict[int, tuple[int, int]] = {}

    used: set[int] = set()

    def window(length: int, lo: int = 30) -> int:
        """A start day with a clear margin, not overlapping other events."""
        for _ in range(200):
            s = rng.randint(lo, days - length - 8)
            if not any(x in used for x in range(s - 3, s + length + 5)):
                used.update(range(s, s + length))
                return s
        s = rng.randint(lo, days - length - 2)
        used.update(range(s, s + length))
        return s

    for kind in plan:
        if kind == "drift":
            s, ramp, hold = window(21), 7, 14
            rise = max(18, 152 - base_sys)  # lands clearly over 140 whatever their normal
            for i in range(s, min(days, s + ramp + hold)):
                sys_add[i] = rise * min(1.0, (i - s + 1) / ramp)
            p.events.append(Event("drift", start + timedelta(s), start + timedelta(s + ramp + hold - 1), "4", f"systolic +{rise} over a week, held"))
        elif kind == "red_bp":
            s = window(1)
            forced_bp[s] = (rng.randint(182, 196), rng.randint(104, 118))
            text_kind[s] = "fine_high"
            p.events.append(Event("red_flag_bp", start + timedelta(s), start + timedelta(s), "R", "'I'm fine' with a reading past the floor"))
        elif kind == "red_symptom":
            s = window(1)
            text_kind[s] = "red_symptom"
            p.events.append(Event("red_flag_symptom", start + timedelta(s), start + timedelta(s), "R", "danger symptom in passing"))
        elif kind == "missed_run":
            s = window(4)
            for i in range(s, s + 4):
                missed[i] = True
            p.events.append(Event("missed_medicine", start + timedelta(s), start + timedelta(s + 3), "4", "4 days of missed BP medicine"))
        elif kind == "haze_week":
            s = window(7)
            for i in range(s, s + 7):
                psi[i] = rng.randint(130, 180)
                steps_mult[i] = 0.35
                social[i] = False
            p.events.append(Event("haze_week", start + timedelta(s), start + timedelta(s + 6), "none", "PSI 130-180, stays in"))
        elif kind == "rainy_week":
            s = window(7)
            for i in range(s, s + 7):
                rain[i] = round(rng.uniform(8, 40), 1)
                steps_mult[i] = 0.35
                social[i] = False
                text_kind[i] = text_kind[i] or ("rain" if rng.random() < 0.5 else None)
            p.events.append(Event("rainy_week", start + timedelta(s), start + timedelta(s + 6), "none", "heavy rain, stays in"))
        elif kind == "mahjong_days":
            s = window(4)
            for i in range(s, s + 4):
                steps_mult[i] = 0.12
                text_kind[i] = text_kind[i] or "mahjong"
            p.events.append(Event("mahjong_days", start + timedelta(s), start + timedelta(s + 3), "none", "~600 steps but a social day"))
        elif kind == "phone_home":
            s = window(2)
            for i in range(s, s + 2):
                no_phone[i] = True
            p.events.append(Event("phone_home", start + timedelta(s), start + timedelta(s + 1), "none", "phone left at home: no steps, no reply"))
        elif kind == "unwell_run":
            s = window(3)
            for i in range(s, s + 3):
                text_kind[i] = "unwell"
            p.events.append(Event("unwell", start + timedelta(s), start + timedelta(s + 2), "4", "unwell three days running"))
        elif kind == "isolation":
            s = window(14)
            for i in range(s, s + 14):
                steps_mult[i] = 0.3
                social[i] = False
                text_kind[i] = text_kind[i] or ("home" if rng.random() < 0.6 else None)
            p.events.append(Event("isolation", start + timedelta(s), start + timedelta(s + 13), "4", "two weeks of low movement and low contact"))
        elif kind == "cny_spike":
            s = (date(2026, 2, 17) - start).days - 1
            for i in range(max(0, s), min(days, s + 5)):
                sys_add[i] = 13
                used.add(i)
            p.events.append(Event("cny_spike", start + timedelta(s), start + timedelta(s + 4), "none", "CNY spike that settles by itself"))

    for i in range(days):
        d = start + timedelta(i)
        if no_phone[i]:
            continue  # phone at home: no steps, no reply, and no reading typed in
        if i in forced_bp or rng.random() < 0.8:
            s, dia = forced_bp.get(i, (round(rng.gauss(base_sys + sys_add[i], 5)), round(rng.gauss(base_dia + sys_add[i] * 0.5, 4))))
            p.readings.append({"id": f"{sid}-bp-{i}", "senior_id": sid, "time": _t(d, "08:05"), "kind": "bp",
                               "values": {"systolic": s, "diastolic": dia, "pulse": rng.randint(62, 84)}, "source": "synthetic", "confidence": 1})
        steps = max(0, round(rng.gauss(base_steps * steps_mult[i], base_steps * 0.12)))
        p.readings.append({"id": f"{sid}-steps-{i}", "senior_id": sid, "time": _t(d, "21:00"), "kind": "steps",
                           "values": {"count": steps}, "source": "synthetic", "confidence": 1})
        replies = []
        if text_kind[i] == "fine_high":
            s, dia = forced_bp[i]
            replies.append(rng.choice(PHRASES[lang]["fine_high"]).format(s=s, d=dia))
        elif text_kind[i]:
            replies.append(rng.choice(PHRASES[lang][text_kind[i]]))
        elif rng.random() < 0.85:
            replies.append(rng.choice(PHRASES[lang]["social" if social[i] else "ok"]))
        replies.append(rng.choice(PHRASES[lang]["forgot" if missed[i] else "took"]))
        for j, text in enumerate(replies):
            p.checkins.append({"id": f"{sid}-ck-{i}-{j}", "senior_id": sid, "time": _t(d, f"0{8 + j}:30"),
                               "source": "synthetic", "raw_text": text, "language": lang})
        p.env.append({"date": d.isoformat(), "region": region, "psi_24h": psi[i], "rainfall_mm": rain[i]})
    return p


def generate(seed: int, n: int, *, prefix: str) -> list[Persona]:
    """n personas from one seed. Every fifth starts in January so CNY falls in its window."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        start = date(2026, 1, 20) if i % 5 == 4 else date(2026, 7, 15)
        out.append(make_persona(rng, i, prefix=prefix, start=start, path="aac" if i % 4 == 3 else "family"))
    return out
