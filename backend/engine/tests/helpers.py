"""Build a senior with a calm 40-day history, then script the days a test cares about."""
from __future__ import annotations

from datetime import date, timedelta

from backend.api.store import Store
from backend.engine import run_day, trust_check
from backend.language import understand
from backend.language.gateway import Chain

NO_MODEL = Chain([])
START = date(2026, 8, 1)
TODAY = START + timedelta(days=40)


class World:
    def __init__(self, *, path: str = "family", lang: str = "en-SG", family_sees: str = "readings", **senior):
        self.store = Store(":memory:")
        self.sid = "s1"
        self.senior = {
            "id": self.sid, "name": "Mr Lim", "language": lang, "home_postal": "560123", "region": "central", "path": path,
            "aac_id": "aac-000", "conditions": ["hypertension"],
            "medicines": [{"name": "amlodipine", "dose_text": "5 mg once a day", "schedule": ["morning"], "started": "2024-01-01", "for_bp": True}],
            "likes": ["mahjong", "karaoke"], "usual_checkin_time": "08:00",
            "consent": {"family_sees": family_sees, "share_words": True, "share_activity": True}, "hidden_suggestions": [], **senior,
        }
        self.store.put("senior", self.senior)
        self.store.put("caregiver", {"id": "cg-1", "name": "Wei Ling" if path != "aac" else "AAC befriender",
                                     "language": "en", "role": path, "worker_id": "aac-000" if path == "aac" else None})
        self.store.put("contact", {"id": "c1", "caregiver_id": "cg-1", "senior_id": self.sid, "role": path, "primary": True,
                                   "name": "AAC befriender" if path == "aac" else "Wei Ling", "language": "en",
                                   "worker_id": "aac-000" if path == "aac" else None})
        self.n = 0
        for i in range(40):
            d = START + timedelta(i)
            self.day(d, bp=(128 + i % 4, 80 + i % 3), text="Ok lah, today fine. Eat medicine already.", steps=5000, psi=40, rain=0)
            run_day(self.store, self.sid, d, gateway=NO_MODEL)

    def day(self, d: date, *, bp=None, text=None, steps: int | None = 5000, psi: int | None = 40, rain: float | None = 0.0,
            glucose=None, gateway=NO_MODEL, lang=None):
        self.n += 1
        t = lambda hhmm: f"{d.isoformat()}T{hhmm}:00+08:00"
        if bp is not None:
            r = {"id": f"bp{self.n}", "senior_id": self.sid, "time": t("08:05"), "kind": "bp",
                 "values": {"systolic": bp[0], "diastolic": bp[1]}, "source": "cuff", "confidence": 1}
            self.store.put("reading", {**r, "trust": trust_check(r)})
        if glucose is not None:
            r = {"id": f"gl{self.n}", "senior_id": self.sid, "time": t("08:10"), "kind": "glucose",
                 "values": {"value": glucose[0], "unit": glucose[1]}, "source": "cuff", "confidence": 1}
            self.store.put("reading", {**r, "trust": trust_check(r)})
        if steps is not None:
            r = {"id": f"st{self.n}", "senior_id": self.sid, "time": t("21:00"), "kind": "steps",
                 "values": {"count": steps}, "source": "synthetic", "confidence": 1}
            self.store.put("reading", {**r, "trust": trust_check(r)})
        if text is not None:
            facts = understand(text, lang or self.senior["language"], gateway=gateway)
            self.store.put("checkin", {"id": f"ck{self.n}", "senior_id": self.sid, "time": t("08:30"), "source": "voice",
                                       "raw_text": text, "language": lang or self.senior["language"], "facts": facts.to_dict()})
        self.store.put("envday", {"id": f"env-{d}-central", "date": d.isoformat(), "region": "central", "psi_24h": psi,
                                  "rainfall_mm": rain, "forecast": None, "festival": None, "source": "synthetic"})

    def run(self, d: date) -> dict:
        return run_day(self.store, self.sid, d, gateway=NO_MODEL)

    def messages(self, decision: dict) -> list[dict]:
        return [self.store.get("message", m) for m in decision["message_ids"]]
