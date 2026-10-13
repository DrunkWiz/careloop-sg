"""GET /senior/{id}/insights and /activities: patterns and things to do, with consent applied for family."""
import unittest

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store


class Insights(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        api.use_store(self.store)
        demo.seed(self.store)
        self.c = TestClient(api.app)
        self.c.post("/demo/advance", json={"days": 11})

    def consent(self, sid, **kw):
        s = self.store.get("senior", sid)
        s["consent"] = {**s["consent"], **kw}
        self.store.put("senior", s)

    def test_the_drift_is_found_as_a_trend(self):
        d = self.c.get("/senior/tan/insights?contact=tan-weiling").json()
        ids = {f["id"]: f for f in d["findings"]}
        self.assertEqual(d["bp"]["trend"], "rising")
        self.assertEqual(ids["bp_trend"]["tone"], "watch")
        self.assertEqual(d["findings"][0]["tone"], "watch")  # things to watch come first
        self.assertTrue(all(f["n"] > 0 and f["title"] and f["detail"] for f in d["findings"]))
        self.assertEqual(len(d["adherence"]["calendar"]), 30)

    def test_quiet_senior_reads_steady(self):
        d = self.c.get("/senior/goh/insights").json()
        self.assertEqual(d["bp"]["trend"], "steady")
        self.assertFalse(any(f["tone"] == "watch" and f["id"].startswith("bp") for f in d["findings"]))

    def test_digest_consent_drops_numbers(self):
        self.consent("tan", family_sees="digest")
        d = self.c.get("/senior/tan/insights?contact=tan-weiling").json()
        self.assertEqual(d["bp"]["series"], [])
        self.assertIsNone(d["bp"]["baseline"])
        self.assertEqual(d["bp"]["trend"], "rising")  # the direction is still shared
        for f in d["findings"]:
            if f["id"].startswith("bp"):
                self.assertNotRegex(f["detail"], r"\d{3}")

    def test_nothing_consent_is_refused(self):
        self.consent("tan", family_sees="nothing")
        self.assertEqual(self.c.get("/senior/tan/insights?contact=tan-weiling").status_code, 403)

    def test_activity_consent_drops_steps_and_answers(self):
        self.consent("tan", share_activity=False)
        self.assertIsNone(self.c.get("/senior/tan/insights?contact=tan-weiling").json()["activity"])
        a = self.c.get("/senior/tan/activities?contact=tan-weiling").json()
        self.assertTrue(all(s["response"] is None for s in a["suggestions"]))

    def test_activities_are_pulled_in_and_nothing_is_stored(self):
        before = len(self.store.list("suggestion"))
        a = self.c.get("/senior/tan/activities?contact=tan-weiling").json()
        self.assertEqual(len(self.store.list("suggestion")), before)
        self.assertTrue(a["own_aac"]["programmes"])
        self.assertEqual(len(a["nearby_ccs"]), 3)
        self.assertEqual([p["km"] for p in a["nearby_ccs"]], sorted(p["km"] for p in a["nearby_ccs"]))
        self.assertLessEqual(len(a["suggested_today"]), 3)
        if a["indoor_only"]:
            self.assertTrue(all(s["indoor"] for s in a["suggested_today"]))

    def test_stranger_is_refused(self):
        self.assertEqual(self.c.get("/senior/tan/insights?contact=wong-mei").status_code, 403)
        self.assertEqual(self.c.get("/senior/tan/activities?contact=wong-mei").status_code, 403)


if __name__ == "__main__":
    unittest.main()
