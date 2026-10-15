"""API tests for the sibling rota: CRUD, validation, on_duty in views, demo integration."""
import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store


class RotaApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)
        # Ensure the demo rota exists for Mr Tan
        rota = self.store.get("rota", "rota-tan")
        if not rota:
            start = demo.DEMO_TODAY - timedelta(days=40)
            self.store.put("rota", {"id": "rota-tan", "senior_id": "tan", "mode": "weekly",
                                    "start_date": start.isoformat(), "order": ["tan-weiling", "tan-kelvin"], "swaps": []})

    def test_17_put_then_get_round_trips(self):
        """PUT a rota then GET it back; on_duty matches the demo today."""
        start = (demo.DEMO_TODAY - timedelta(days=40)).isoformat()
        r = self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["tan-weiling", "tan-kelvin"]})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["rota"]["mode"], "weekly")
        self.assertEqual(body["rota"]["order"], ["tan-weiling", "tan-kelvin"])

        # GET it back
        r2 = self.c.get("/senior/tan/rota")
        self.assertEqual(r2.status_code, 200)
        body2 = r2.json()
        self.assertEqual(body2["rota"]["order"], ["tan-weiling", "tan-kelvin"])
        # on_duty should be a real contact
        self.assertIsNotNone(body2["on_duty"])
        self.assertIn(body2["on_duty"]["id"], ["tan-weiling", "tan-kelvin"])

    def test_18_put_with_invalid_contact_returns_400(self):
        """PUT with an unknown contact, another senior's contact, an AAC contact, or a duplicate → 400."""
        start = (demo.DEMO_TODAY - timedelta(days=40)).isoformat()
        # Unknown contact
        r = self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["no-such-contact"]})
        self.assertEqual(r.status_code, 400)
        # Another senior's contact (wong-mei is Mdm Wong's contact)
        r = self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["wong-mei"]})
        self.assertEqual(r.status_code, 400)
        # AAC contact (aac-siti:lee is an AAC contact)
        r = self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["aac-siti:lee"]})
        self.assertEqual(r.status_code, 400)
        # Duplicate
        r = self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["tan-weiling", "tan-weiling"]})
        self.assertEqual(r.status_code, 400)

    def test_19_get_put_unknown_senior_returns_404(self):
        """GET/PUT on an unknown senior → 404."""
        start = demo.DEMO_TODAY.isoformat()
        self.assertEqual(self.c.get("/senior/no-such-senior/rota").status_code, 404)
        r = self.c.put("/senior/no-such-senior/rota", json={"mode": "weekly", "start_date": start, "order": []})
        self.assertEqual(r.status_code, 404)

    def test_20_swap_valid_and_invalid(self):
        """swap: valid → 200 and on_duty changes for that date; an invalid contact → 400."""
        start = (demo.DEMO_TODAY - timedelta(days=40)).isoformat()
        self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["tan-weiling", "tan-kelvin"]})
        # Determine who's on duty today
        today = demo.DEMO_TODAY
        before = self.c.get("/senior/tan/rota").json()
        on_duty_id = before["on_duty"]["id"]
        # The other contact
        other = "tan-kelvin" if on_duty_id == "tan-weiling" else "tan-weiling"
        # Swap: put the other contact on duty for today
        r = self.c.post("/senior/tan/rota/swap", json={"date": today.isoformat(), "contact_id": other})
        self.assertEqual(r.status_code, 200)
        # Verify on_duty changes for today
        after = self.c.get("/senior/tan/rota").json()
        self.assertEqual(after["on_duty"]["id"], other)
        # Invalid contact → 400
        r = self.c.post("/senior/tan/rota/swap", json={"date": today.isoformat(), "contact_id": "no-such-contact"})
        self.assertEqual(r.status_code, 400)

    def test_21_delete_rota_rung4_goes_to_primary(self):
        """DELETE rota → rung 4 goes back to primary."""
        # Delete the rota
        r = self.c.delete("/senior/tan/rota")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.json()["rota"])
        # Trigger a rung-4 on a fresh day by advancing the demo
        self.c.post("/demo/advance", json={"days": 1})
        t = demo.today(self.store)
        dec = self.store.get("decision", f"dec-tan-{t.isoformat()}")
        if dec and dec["rung"] == "4":
            fam_msgs = [m for m in self.store.list("message", senior_id="tan", day_from=t.isoformat()) if m["to"] == "family"]
            # Primary is tan-weiling
            self.assertTrue(any(m["contact_id"] == "tan-weiling" for m in fam_msgs))
            self.assertFalse(any(m["contact_id"] == "tan-kelvin" for m in fam_msgs))
        # Restore the rota for other tests
        start = (demo.DEMO_TODAY - timedelta(days=40)).isoformat()
        self.store.put("rota", {"id": "rota-tan", "senior_id": "tan", "mode": "weekly",
                                "start_date": start, "order": ["tan-weiling", "tan-kelvin"], "swaps": []})

    def test_22_family_view_on_duty(self):
        """/care/family/tan-kelvin shows on_duty true in Kelvin's week, false in Wei Ling's."""
        start = (demo.DEMO_TODAY - timedelta(days=40)).isoformat()
        self.c.put("/senior/tan/rota", json={"mode": "weekly", "start_date": start, "order": ["tan-weiling", "tan-kelvin"]})
        today = demo.DEMO_TODAY
        # Find which week we're in
        days_since = (today - date.fromisoformat(start)).days
        kelvin_week = (days_since // 7) % 2 == 1
        view = self.c.get("/care/family/tan-kelvin").json()
        if kelvin_week:
            self.assertTrue(view["on_duty"])
        else:
            self.assertFalse(view["on_duty"])
        # Check on_duty_name is present
        self.assertIn("on_duty_name", view)

    def test_23_caregiver_view_on_duty_per_senior(self):
        """/care/caregiver/cg-kelvin shows on_duty per senior."""
        view = self.c.get("/care/caregiver/cg-kelvin").json()
        self.assertTrue(len(view["seniors"]) >= 1)
        for s in view["seniors"]:
            self.assertIn("on_duty", s)
            self.assertIsInstance(s["on_duty"], bool)

    def test_24_rota_validates_against_schema(self):
        """Every stored rota validates against Rota.schema.json."""
        from backend.api.tests.test_api import validate
        for rota in self.store.list("rota"):
            validate("Rota", rota)

    def test_25_demo_reset_advance_red_flag_reaches_both(self):
        """The demo still works: reset + advance 11 days, the red flag reaches both Wei Ling and Kelvin."""
        self.c.post("/demo/reset")
        self.c.post("/demo/advance", json={"days": 11})
        # Post a red-flag check-in for Mr Tan
        r = self.c.post("/checkin", json={"senior_id": "tan", "text": "I feel fine lah, BP 190/125 this morning", "source": "voice"})
        self.assertEqual(r.json()["rung"], "R")
        t = demo.today(self.store)
        fam_msgs = [m for m in self.store.list("message", senior_id="tan", day_from=t.isoformat()) if m["to"] == "family" and m["rung"] == "R"]
        contacts = {m["contact_id"] for m in fam_msgs}
        self.assertIn("tan-weiling", contacts)
        self.assertIn("tan-kelvin", contacts)


if __name__ == "__main__":
    unittest.main()
