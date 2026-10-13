"""GET/PUT /senior/{id}/care-notes: shared by every linked contact, closed to everyone else, and the
family's questions and next visit reach the GP brief."""
import unittest

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store

NOTES = {
    "appointments": [{"id": "a1", "date": "2026-10-30", "time": "9:30am", "place": "Ang Mo Kio Polyclinic", "purpose": "BP review"}],
    "questions": [{"id": "q1", "text": "Should the dose be reviewed?", "by": "Wei Ling"},
                  {"id": "q2", "text": "Already asked", "by": "Kelvin", "asked": True}],
    "tasks": [{"id": "t1", "title": "Collect refill", "owner": "Kelvin"}],
    "emergency": {"allergies": "Penicillin", "gp_name": "Sample Clinic"},
}


class CareNotes(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        api.use_store(self.store)
        demo.seed(self.store)
        self.c = TestClient(api.app)

    def test_empty_until_written(self):
        d = self.c.get("/senior/tan/care-notes?contact=tan-weiling").json()
        self.assertEqual(d["tasks"], [])
        self.assertIsNone(d["updated_by"])

    def test_shared_between_contacts(self):
        self.assertEqual(self.c.put("/senior/tan/care-notes?contact=tan-weiling", json=NOTES).status_code, 200)
        d = self.c.get("/senior/tan/care-notes?contact=tan-kelvin").json()
        self.assertEqual(d["tasks"][0]["owner"], "Kelvin")
        self.assertEqual(d["updated_by"], "Wei Ling")
        self.assertEqual(d["emergency"]["allergies"], "Penicillin")

    def test_strangers_are_refused(self):
        self.assertEqual(self.c.get("/senior/tan/care-notes").status_code, 403)
        self.assertEqual(self.c.get("/senior/tan/care-notes?contact=wong-mei").status_code, 403)
        self.assertEqual(self.c.put("/senior/tan/care-notes?contact=wong-mei", json=NOTES).status_code, 403)

    def test_aac_contact_can_keep_notes(self):
        self.assertEqual(self.c.put("/senior/lee/care-notes?contact=aac-siti:lee", json=NOTES).status_code, 200)

    def test_bad_input_is_rejected(self):
        bad = {**NOTES, "appointments": [{"id": "a1", "date": "next tuesday"}]}
        self.assertEqual(self.c.put("/senior/tan/care-notes?contact=tan-weiling", json=bad).status_code, 422)

    def test_unasked_questions_and_next_visit_reach_the_brief(self):
        self.c.put("/senior/tan/care-notes?contact=tan-weiling", json=NOTES)
        b = self.c.get("/senior/tan/brief.json").json()
        self.assertEqual(b["family_questions"], ["Should the dose be reviewed?"])
        self.assertEqual(b["next_appointment"]["place"], "Ang Mo Kio Polyclinic")

    def test_notes_never_change_a_decision(self):
        self.c.post("/demo/advance", json={"days": 3})
        before = [d["rung"] for d in self.store.list("decision", senior_id="tan")]
        self.c.put("/senior/tan/care-notes?contact=tan-weiling", json=NOTES)
        after = [d["rung"] for d in self.store.list("decision", senior_id="tan")]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
