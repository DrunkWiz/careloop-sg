"""GET /senior/{id}/log: every day's decision, with the senior's consent applied for family."""
import unittest

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store


class DecisionLog(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        api.use_store(self.store)
        demo.seed(self.store)
        self.c = TestClient(api.app)
        self.c.post("/demo/advance", json={"days": 11})

    def set_consent(self, sid, **kw):
        """Per-link consent: set on the contact, not the senior."""
        c = self.store.get("contact", f"{sid}-weiling")
        c["consent"] = {**(c.get("consent") or {}), **kw}
        self.store.put("contact", c)

    def test_every_day_has_a_decision_newest_first(self):
        log = self.c.get("/senior/tan/log?days=14").json()
        self.assertEqual(len(log), 14)
        self.assertGreater(log[0]["date"], log[-1]["date"])
        decided = [d for d in log if d["rung"] is not None]
        self.assertGreaterEqual(len(decided), 12)  # a day with no data yet has no decision, and says so
        self.assertTrue(all(d["rule_id"] and d["decision_id"] for d in decided))
        self.assertIn("0", {d["rung"] for d in log})  # quiet days are logged too
        self.assertEqual(log[0]["rung"], "4")

    def test_aac_sees_everything(self):
        log = self.c.get("/senior/lee/log?days=7&contact=aac-siti:lee").json()
        self.assertTrue(any(d["reason"] for d in log))
        self.assertTrue(any(d["checkins"] for d in log))

    def test_family_readings_consent_shows_numbers(self):
        self.set_consent("tan", family_sees="readings", share_words=True)
        log = self.c.get("/senior/tan/log?days=7&contact=tan-weiling").json()
        self.assertTrue(any(d["bp"] for d in log))
        self.assertTrue(any(d["checkins"] for d in log))

    def test_family_digest_consent_hides_numbers_and_reasons(self):
        self.set_consent("tan", family_sees="digest", share_words=False)
        log = self.c.get("/senior/tan/log?days=7&contact=tan-weiling").json()
        self.assertTrue(all(d["bp"] is None and d["reason"] is None for d in log))
        self.assertTrue(all(d["checkins"] == [] for d in log))
        self.assertTrue(any(d["rule_id"] for d in log))  # what kind of day it was still shows

    def test_family_nothing_consent_hides_all_but_red_flags(self):
        self.set_consent("tan", family_sees="nothing")
        self.c.post("/checkin", json={"senior_id": "tan", "text": "chest pain since morning", "language": "en"})
        log = self.c.get("/senior/tan/log?days=7&contact=tan-weiling").json()
        self.assertEqual(log[0]["rung"], "R")
        self.assertIsNotNone(log[0]["reason"])  # red flags are always shared
        self.assertTrue(all(d["rung"] is None and d["reason"] is None for d in log[1:]))

    def test_stranger_is_refused(self):
        self.assertEqual(self.c.get("/senior/tan/log?contact=wong-mei").status_code, 403)
        self.assertEqual(self.c.get("/senior/nobody/log").status_code, 404)


if __name__ == "__main__":
    unittest.main()
