"""Medicines explained and the staying-well checklist through the API, and their place on the GP brief."""
import unittest

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store


class MedicinesApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store, days=20)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_medicines_in_the_seniors_language(self):
        r = self.c.get("/senior/chandran/medicines").json()
        self.assertEqual([m["known"] for m in r["medicines"]], [True, False])  # Zanidip isn't in the notes
        zh = self.c.get("/senior/wong/medicines").json()
        self.assertEqual(zh["medicines"][0]["what_for"], "降血压。")
        en = self.c.get("/senior/wong/medicines?lang=en&contact=wong-mei").json()
        self.assertEqual(en["medicines"][0]["what_for"], "Lowers blood pressure.")
        self.assertEqual(self.c.get("/senior/wong/medicines?contact=tan-weiling").status_code, 403)

    def test_prevention_reads_the_care_plan(self):
        items = {i["id"]: i for i in self.c.get("/senior/tan/prevention?contact=tan-kelvin").json()["items"]}
        self.assertEqual(items["flu"]["status"], "due")
        self.assertEqual(items["bp_review"]["status"], "booked")
        rahman = {i["id"] for i in self.c.get("/senior/rahman/prevention").json()["items"]}
        self.assertIn("diabetes_eye", rahman)

    def test_ticking_off_and_bad_dates(self):
        notes = self.c.get("/senior/kaur/care-notes?contact=kaur-priya").json()
        body = {k: notes[k] for k in ("appointments", "questions", "tasks", "emergency")}
        ok = self.c.put("/senior/kaur/care-notes?contact=kaur-priya", json={**body, "prevention": {"flu": api.today().isoformat()}})
        self.assertEqual(ok.status_code, 200)
        items = {i["id"]: i for i in self.c.get("/senior/kaur/prevention").json()["items"]}
        self.assertEqual(items["flu"]["status"], "done")
        for bad in ({"flu": "2099-01-01"}, {"flu": "soon"}, {"made_up": "2026-01-01"}):
            with self.subTest(bad):
                r = self.c.put("/senior/kaur/care-notes?contact=kaur-priya", json={**body, "prevention": bad})
                self.assertEqual(r.status_code, 400)

    def test_gp_brief_lists_whats_due(self):
        due = self.c.get("/senior/tan/brief.json").json()["prevention_due"]
        self.assertIn("Flu vaccine (due)", due)
        self.assertEqual(self.c.get("/senior/tan/brief.pdf").status_code, 200)


if __name__ == "__main__":
    unittest.main()
