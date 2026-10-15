"""The demo has a care plan for Mr Tan and a timetable for the AAC-path seniors' centre, so the Plan tab and
the centre's Programmes page aren't empty in the video."""
import unittest

from backend.api import demo
from backend.api.store import Store


class DemoPlansTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        demo.seed(cls.store, days=20)

    def test_mr_tan_has_a_care_plan(self):
        notes = self.store.get("carenotes", "notes-tan")
        self.assertTrue(any(a["date"] > demo.DEMO_TODAY.isoformat() for a in notes["appointments"]))
        self.assertTrue(any(not q["asked"] for q in notes["questions"]))
        self.assertIn("(demo", notes["emergency"]["gp_name"])

    def test_centre_has_a_timetable(self):
        progs = [p for p in self.store.list("programme") if p["place_id"] == "aac-105"]
        self.assertGreater(len(progs), 0)
        self.assertFalse(any(p["sample"] for p in progs))


if __name__ == "__main__":
    unittest.main()
