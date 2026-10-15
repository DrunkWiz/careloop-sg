"""Phone health data through the API: Health Connect and Apple Health records become readings, a synced
red-flag BP is a red flag, consent applies to family, and the demo's phone can sync again without counting twice."""
import unittest

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store
from backend.healthsync.simulate import phone_day


class HealthSyncApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store, days=20)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def records(self, platform, sid="wong", **kw):
        t = api.now()
        return phone_day(sid, t.date(), platform=platform, upto=t, **kw), t

    def test_a_sync_becomes_readings_and_shows_as_connected(self):
        recs, t = self.records("health_connect", steps=4000, resting_hr=70, sleep_hours=6.8)
        r = self.c.post("/senior/wong/health-sync", json={"platform": "health_connect", "records": recs}).json()
        self.assertEqual(r["status"]["platform_name"], "Health Connect")
        self.assertEqual(r["status"]["apps"], ["Fitbit"] if recs else [])
        v = self.c.get("/senior/wong/health-sync?contact=wong-mei").json()
        self.assertTrue(v["connected"])
        self.assertEqual(v["days"][-1]["date"], t.date().isoformat())

    def test_a_synced_red_flag_reading_is_a_red_flag(self):
        recs, _ = self.records("healthkit", sid="goh", apps=("omron",), bp=[(api.now().strftime("%H:%M"), 186, 112)])
        r = self.c.post("/senior/goh/health-sync", json={"platform": "healthkit", "records": recs}).json()
        self.assertEqual(r["imported"], {"bp": 1})
        self.assertEqual(r["rung"], "R")

    def test_consent_digest_hides_readings_from_family(self):
        recs, _ = self.records("health_connect", sid="chua", apps=("fitbit", "omron"), steps=3000,
                               bp=[(api.now().strftime("%H:%M"), 131, 80)])
        self.c.post("/senior/chua/health-sync", json={"platform": "health_connect", "records": recs})
        v = self.c.get("/senior/chua/health-sync?contact=chua-junjie").json()
        self.assertFalse(v["shares_readings"])
        self.assertEqual([d["bp"] for d in v["days"]], [[]] * len(v["days"]))
        self.assertEqual(self.c.get("/senior/chua/health-sync?contact=tan-weiling").status_code, 403)

    def test_unknown_platform_is_refused(self):
        self.assertEqual(self.c.post("/senior/wong/health-sync", json={"platform": "garmin", "records": []}).status_code, 422)

    def test_demo_phone_syncs_again_without_counting_twice(self):
        a = self.c.post("/demo/health-sync/rahman").json()
        steps = lambda: (self.store.get("reading", f"hs-rahman-steps-{api.today()}") or {"values": {"count": 0}})["values"]["count"]
        first = steps()
        b = self.c.post("/demo/health-sync/rahman").json()
        self.assertEqual(steps(), first)
        self.assertEqual(a["status"]["platform_name"], "Health Connect")
        self.assertEqual(b["skipped"], 0)
        self.assertEqual(self.c.post("/demo/health-sync/wong").status_code, 409)  # no phone in the demo

    def test_demo_phone_through_the_day(self):
        """Fixed times, so it doesn't depend on when the tests run: a repeat sync changes nothing, and the
        total only grows as the hours pass, up to the day's plan."""
        from datetime import datetime

        from backend.healthsync.mapping import SGT

        d = api.today()
        counts = []
        for hh in (9, 9, 13, 22):
            demo.phone_sync(self.store, "lim", datetime(d.year, d.month, d.day, hh, 30, tzinfo=SGT))
            counts.append(self.store.get("reading", f"hs-lim-steps-{d}")["values"]["count"])
        self.assertEqual(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])
        self.assertLess(counts[2], counts[3])

    def test_demo_cuff_reading(self):
        r = self.c.post("/demo/health-sync/kaur", json={"bp": [133, 81]}).json()
        self.assertEqual(r["imported"].get("bp"), 1)
        self.assertEqual(r["status"]["platform_name"], "Apple Health")


CSV = "Programme,Days,Time\nMorning exercise,Mon/Wed/Fri,8:30am\nKaraoke,Sat,10am\n"


class TimetableImportApi(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        api.use_store(self.store)
        demo.seed(self.store, days=20)
        self.c = TestClient(api.app)

    def test_preview_then_save(self):
        preview = self.c.post("/aac/aac-100/programmes/import", json={"text": CSV}).json()
        self.assertFalse(preview["saved"])
        self.assertEqual([p["title"] for p in preview["programmes"]], ["Morning exercise", "Karaoke"])
        self.assertEqual(self.c.get("/aac/aac-100/programmes").json(), [])
        saved = self.c.post("/aac/aac-100/programmes/import", json={"text": CSV, "save": True}).json()
        self.assertTrue(saved["saved"])
        self.assertEqual(len(self.c.get("/aac/aac-100/programmes").json()), 2)

    def test_a_calendar_link_is_pulled_again_after_a_day(self):
        calls = []
        real = api._fetch
        api._fetch = lambda url: calls.append(url) or CSV
        try:
            self.c.post("/aac/aac-100/programmes/import", json={"url": "https://example.test/centre.ics", "save": True})
            self.c.get("/aac/aac-100/programmes")
            self.assertEqual(len(calls), 1)  # fresh: not pulled again
            feed = api._feed("aac-100")
            feed["pulled_at"] = "2020-01-01T00:00:00+08:00"
            self.store.set_setting("programme_feed:aac-100", api.json.dumps(feed))
            self.c.get("/aac/aac-100/programmes")
            self.assertEqual(len(calls), 2)
        finally:
            api._fetch = real

    def test_nothing_to_import(self):
        self.assertEqual(self.c.post("/aac/aac-100/programmes/import", json={}).status_code, 400)
        self.assertEqual(self.c.post("/aac/aac-100/programmes/import", json={"url": "file:///etc/passwd"}).status_code, 400)


class DemoPeople(unittest.TestCase):
    """The fortnight's scripts for the seniors added on 15 Oct (see backend/api/demo.py)."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        demo.seed(cls.store)
        demo.advance(cls.store, 11)

    def kinds(self, sid):
        return {h["kind"] for h in self.store.list("handover", senior_id=sid)}

    def test_stories(self):
        self.assertEqual(self.kinds("tan"), {"bp_drift"})  # the video, unchanged
        self.assertEqual(self.kinds("chandran"), {"bp_drift"})  # drift seen through his synced cuff
        self.assertEqual(self.kinds("osman"), {"no_contact"})  # silent, no steps, dry days
        self.assertEqual(self.kinds("lim"), set())  # silent, but his watch shows him walking
        self.assertEqual(self.kinds("kaur"), set())
        rules = {d["rule_id"] for d in self.store.list("decision", senior_id="rahman")}
        self.assertIn("2.missed_pattern", rules)

    def test_two_centres_and_more_caregivers(self):
        workers = {c["worker_id"] for c in self.store.list("contact") if c["role"] == "aac"}
        self.assertEqual(workers, {"aac-siti", "aac-farid"})
        family = [c for c in self.store.list("contact") if c["role"] == "family"]
        self.assertEqual(len(family), 11)  # 9 + Mrs Teo's two (Kelvin and Jane)
        self.assertEqual(len(self.store.list("senior")), 13)


if __name__ == "__main__":
    unittest.main()
