"""Health Connect and Apple Health records become the same CareLoop readings; syncing again changes nothing."""
import json
import unittest
from datetime import date, datetime
from pathlib import Path

from backend.api.store import Store
from backend.healthsync import ingest, parse, to_readings
from backend.healthsync.ingest import recent
from backend.healthsync.mapping import SGT
from backend.healthsync.simulate import phone_day

FIX = Path(__file__).resolve().parent.parent / "fixtures"
DAY = date(2026, 10, 24)
NOW = datetime(2026, 10, 24, 10, 30, tzinfo=SGT)


def fixture(name):
    d = json.loads((FIX / name).read_text(encoding="utf-8"))
    return d["platform"], d["records"]


def by_kind(readings):
    return {r["kind"]: r for r in readings}


class MappingTest(unittest.TestCase):
    def test_both_platforms_give_the_same_readings(self):
        for name in ("health_connect_day.json", "healthkit_day.json"):
            with self.subTest(name):
                m = parse(*fixture(name))
                r = by_kind(to_readings("s1", m))
                self.assertEqual(r["steps"]["values"], {"count": 1850})  # the repeated block counts once
                self.assertEqual(r["hr"]["values"], {"bpm": 66})
                self.assertEqual(r["sleep"]["values"], {"hours": 7.0})  # the 20 minutes awake don't count
                self.assertEqual(r["bp"]["values"], {"systolic": 138, "diastolic": 86})
                self.assertEqual(r["bp"]["source"], "cuff")
                self.assertEqual(r["steps"]["source"], "watch")
                self.assertTrue(all(x["time"].startswith("2026-10-24") for x in r.values()))
                self.assertEqual(m.apps, {"Fitbit", "OMRON connect"})
                self.assertEqual(m.skipped, 1)  # weight: not something CareLoop uses

    def test_unknown_platform_is_refused(self):
        with self.assertRaises(ValueError):
            parse("garmin", [])

    def test_wrong_unit_is_skipped_not_converted(self):
        bad = [{"type": "HKQuantityTypeIdentifierRestingHeartRate", "uuid": "x", "startDate": "2026-10-24T07:00:00+08:00",
                "value": 1.1, "unit": "count/s"}]
        m = parse("healthkit", bad)
        self.assertEqual((m.resting_hr, m.skipped), ({}, 1))


class IngestTest(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def steps(self):
        return [r for r in self.store.list("reading", senior_id="s1") if r["kind"] == "steps"]

    def test_syncing_twice_changes_nothing(self):
        platform, records = fixture("health_connect_day.json")
        ingest(self.store, "s1", platform, records, now=NOW)
        ingest(self.store, "s1", platform, records, now=NOW)
        self.assertEqual([r["values"]["count"] for r in self.steps()], [1850])
        self.assertEqual(len(self.store.list("reading", senior_id="s1")), 4)

    def test_a_later_sync_with_only_new_blocks_adds_them(self):
        early = phone_day("s1", DAY, platform="health_connect", steps=5000, upto=datetime(2026, 10, 24, 12, 0, tzinfo=SGT))
        late = phone_day("s1", DAY, platform="health_connect", steps=5000)
        new_only = [r for r in late if r not in early]
        ingest(self.store, "s1", "health_connect", early, now=NOW)
        first = self.steps()[0]["values"]["count"]
        ingest(self.store, "s1", "health_connect", new_only, now=datetime(2026, 10, 24, 23, 59, tzinfo=SGT))
        self.assertLess(first, 5000)
        self.assertEqual(self.steps()[0]["values"]["count"], 5000)

    def test_records_from_the_future_are_skipped(self):
        records = phone_day("s1", date(2026, 10, 26), platform="healthkit", steps=4000, resting_hr=70)
        out = ingest(self.store, "s1", "healthkit", records, now=NOW)
        self.assertEqual(out["readings"], [])
        self.assertGreater(out["skipped"], 0)

    def test_every_reading_is_trust_checked(self):
        records = phone_day("s1", DAY, platform="health_connect", apps=("omron",), bp=[("08:05", 80, 120)])
        ingest(self.store, "s1", "health_connect", records, now=NOW)
        bp = self.store.list("reading", senior_id="s1")[0]
        self.assertEqual(bp["values"], {"systolic": 80, "diastolic": 120})  # never fixed
        self.assertIn("swapped", bp["trust"]["flags"])

    def test_status_and_recent(self):
        platform, records = fixture("healthkit_day.json")
        out = ingest(self.store, "s1", platform, records, now=NOW)
        self.assertEqual(out["status"]["platform_name"], "Apple Health")
        self.assertEqual(out["status"]["apps"], ["Fitbit", "OMRON connect"])
        row = recent(self.store, "s1", DAY)[-1]
        self.assertEqual((row["steps"], row["resting_hr"], row["sleep_hours"]), (1850, 66, 7.0))
        self.assertEqual(len(row["bp"]), 1)


class SimulateTest(unittest.TestCase):
    def test_a_simulated_day_adds_up(self):
        for platform in ("health_connect", "healthkit"):
            with self.subTest(platform):
                rec = phone_day("s1", DAY, platform=platform, apps=("fitbit", "omron"), steps=4321, resting_hr=68,
                                sleep_hours=6.5, bp=[("08:05", 131, 82)])
                r = by_kind(to_readings("s1", parse(platform, rec)))
                self.assertEqual(r["steps"]["values"]["count"], 4321)
                self.assertEqual(r["hr"]["values"]["bpm"], 68)
                self.assertEqual(r["sleep"]["values"]["hours"], 6.5)
                self.assertEqual(r["bp"]["values"], {"systolic": 131, "diastolic": 82})


if __name__ == "__main__":
    unittest.main()
