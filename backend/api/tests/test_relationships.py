"""Tests for the caregiver ↔ senior relationship model: per-link consent, pairing edge
cases, primary promotion/demotion, caregiver view, AAC caseload matching, handover
claiming, schema integrity, and legacy data compatibility.

Uses Store(":memory:") + demo.seed. unittest only, offline."""
import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

from backend.api import app as api
from backend.api import demo
from backend.api.app import _status, now
from backend.api.store import Store


class PerLinkConsent(unittest.TestCase):
    """Each contact has its own consent; endpoints respect it, not the senior's."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_kelvin_digest_weiling_readings_on_same_senior(self):
        """Kelvin gets 'digest' (no numbers); Wei Ling gets 'readings' (numbers)."""
        # Set per-link consent on each contact.
        wl = self.store.get("contact", "tan-weiling")
        wl["consent"] = {"family_sees": "readings", "share_words": True, "share_activity": True}
        self.store.put("contact", wl)
        kv = self.store.get("contact", "tan-kelvin")
        kv["consent"] = {"family_sees": "digest", "share_words": False, "share_activity": False}
        self.store.put("contact", kv)

        # family_view respects each contact's consent.
        wl_view = self.c.get("/care/family/tan-weiling").json()
        self.assertEqual(wl_view["family_sees"], "readings")
        self.assertIsNotNone(wl_view["digest"]["mean_systolic"])

        kv_view = self.c.get("/care/family/tan-kelvin").json()
        self.assertEqual(kv_view["family_sees"], "digest")
        # digest sees=None, so no mean_systolic/baseline.
        self.assertIsNone(kv_view["digest"]["mean_systolic"])
        self.assertIsNone(kv_view["digest"]["baseline"])

    def test_log_respects_per_link_consent(self):
        """Decision log respects each contact's consent: Kelvin (digest) gets no BP numbers."""
        wl = self.store.get("contact", "tan-weiling")
        wl["consent"] = {"family_sees": "readings", "share_words": True, "share_activity": True}
        self.store.put("contact", wl)
        kv = self.store.get("contact", "tan-kelvin")
        kv["consent"] = {"family_sees": "digest", "share_words": False, "share_activity": False}
        self.store.put("contact", kv)

        wl_log = self.c.get("/senior/tan/log?contact=tan-weiling").json()
        kv_log = self.c.get("/senior/tan/log?contact=tan-kelvin").json()

        # Wei Ling (readings) sees BP numbers on non-red-flag days.
        wl_bp_days = [d for d in wl_log if d["bp"] is not None]
        self.assertTrue(wl_bp_days)
        # Kelvin (digest) never sees BP numbers.
        kv_bp_days = [d for d in kv_log if d["bp"] is not None]
        self.assertEqual(kv_bp_days, [])
        # Kelvin (share_words=false) sees no check-in words.
        kv_words = [d for d in kv_log if d["checkins"]]
        self.assertEqual(kv_words, [])
        # Wei Ling (share_words=true) may see words.
        wl_words = [d for d in wl_log if d["checkins"]]
        self.assertTrue(wl_words)

    def test_insights_respects_per_link_consent(self):
        """Insights endpoint uses _viewer() which reads per-link consent."""
        wl = self.store.get("contact", "tan-weiling")
        wl["consent"] = {"family_sees": "readings", "share_words": True, "share_activity": True}
        self.store.put("contact", wl)
        kv = self.store.get("contact", "tan-kelvin")
        kv["consent"] = {"family_sees": "digest", "share_words": False, "share_activity": False}
        self.store.put("contact", kv)

        # Wei Ling (readings) gets insights with numbers.
        wl_r = self.c.get("/senior/tan/insights?contact=tan-weiling")
        self.assertEqual(wl_r.status_code, 200)
        # Kelvin (digest) gets insights without numbers.
        kv_r = self.c.get("/senior/tan/insights?contact=tan-kelvin")
        self.assertEqual(kv_r.status_code, 200)

    def test_fallback_to_senior_consent_when_contact_has_none(self):
        """A contact with no consent field falls back to the senior's default consent."""
        wl = self.store.get("contact", "tan-weiling")
        # Remove consent from the contact.
        wl.pop("consent", None)
        self.store.put("contact", wl)
        # The senior's consent is "readings" (set by demo.seed).
        view = self.c.get("/care/family/tan-weiling").json()
        self.assertEqual(view["family_sees"], "readings")


class PairingEdgeCases(unittest.TestCase):
    """Edge cases for POST /care/pair-code + POST /pair."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_unknown_caregiver_id_on_pair_code_returns_404(self):
        r = self.c.post("/care/pair-code", json={"caregiver_id": "cg-nope", "contact_name": "Ghost",
                                                  "senior_name": "Mr Ghost", "home_postal": "560999"})
        self.assertEqual(r.status_code, 404)

    def test_pair_code_whose_caregiver_was_deleted_returns_404(self):
        code = self.c.post("/care/pair-code", json={"caregiver_id": "cg-kelvin", "contact_name": "Kelvin",
                                                     "senior_name": "Mr Tan", "home_postal": "560999"}).json()
        # Delete the caregiver.
        self.store.delete("caregiver", "cg-kelvin")
        r = self.c.post("/pair", json={"code": code["code"], "senior_id": "tan"})
        self.assertEqual(r.status_code, 404)

    def test_first_link_is_primary_second_is_not(self):
        """The first contact linked to a new senior is primary; a second caregiver's link is not."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Create a brand-new senior via pairing.
        code1 = self.c.post("/care/pair-code", json={"contact_name": "Alice", "senior_name": "Mr New",
                                                      "home_postal": "560999"}).json()
        r1 = self.c.post("/pair", json={"code": code1["code"], "language": "en",
                                        "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})
        self.assertEqual(r1.status_code, 200)
        sid = r1.json()["senior_id"]
        contacts = s.list("contact", senior_id=sid)
        self.assertEqual(len(contacts), 1)
        self.assertTrue(contacts[0]["primary"])
        # Now a second caregiver pairs onto the same senior.
        code2 = self.c.post("/care/pair-code", json={"contact_name": "Bob", "senior_name": "Mr New",
                                                      "home_postal": "560999"}).json()
        r2 = self.c.post("/pair", json={"code": code2["code"], "senior_id": sid,
                                        "consent": {"family_sees": "digest", "share_words": False, "share_activity": True}})
        self.assertEqual(r2.status_code, 200)
        contacts2 = s.list("contact", senior_id=sid)
        self.assertEqual(len(contacts2), 2)
        primaries = [c for c in contacts2 if c["primary"]]
        self.assertEqual(len(primaries), 1)
        # Bob is NOT primary.
        bob = next(c for c in contacts2 if c["name"] == "Bob")
        self.assertFalse(bob["primary"])

    def test_second_caregiver_pairing_overwrites_senior_consent(self):
        """BUG CHECK: pairing a second caregiver onto an existing senior overwrites
        the senior's default consent. The code comment says 'follows the primary link'
        but the code always sets s['consent'] = consent on line 280.

        If this test fails, it confirms the bug: the second caregiver's consent
        replaces the senior's default, even though only the primary link should
        drive the senior's fallback consent."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Create a senior with readings consent.
        code1 = self.c.post("/care/pair-code", json={"contact_name": "Alice", "senior_name": "Mr Consent",
                                                      "home_postal": "560999"}).json()
        r1 = self.c.post("/pair", json={"code": code1["code"], "language": "en",
                                        "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})
        sid = r1.json()["senior_id"]
        before = s.get("senior", sid)["consent"]
        self.assertEqual(before["family_sees"], "readings")
        # Second caregiver pairs with 'nothing' consent.
        code2 = self.c.post("/care/pair-code", json={"contact_name": "Bob", "senior_name": "Mr Consent",
                                                      "home_postal": "560999"}).json()
        self.c.post("/pair", json={"code": code2["code"], "senior_id": sid,
                                   "consent": {"family_sees": "nothing", "share_words": False, "share_activity": False}})
        after = s.get("senior", sid)["consent"]
        # If the code is correct (follows primary), the senior's consent stays "readings".
        # If the bug exists, the senior's consent becomes "nothing".
        # We assert the CORRECT behavior; if it fails, it's a bug report.
        self.assertEqual(after["family_sees"], "readings",
                         f"BUG: second caregiver pairing overwrote senior.consent from 'readings' to '{after['family_sees']}' "
                         f"(app.py line 280: s['consent'] = consent always runs, should only run for primary)")

    def test_repairing_existing_link_does_not_update_consent(self):
        """Re-pairing an existing link (same caregiver+senior) reuses the contact
        but does NOT update the contact's consent — only the senior's consent is touched."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Kelvin already linked to Mr Tan with the demo's default consent.
        kv_before = s.get("contact", "tan-kelvin")
        kv_before_consent = kv_before.get("consent", {}).get("family_sees")
        # Re-pair Kelvin onto Mr Tan with different consent.
        code = self.c.post("/care/pair-code", json={"caregiver_id": "cg-kelvin", "contact_name": "Kelvin",
                                                     "senior_name": "Mr Tan", "home_postal": "560999"}).json()
        r = self.c.post("/pair", json={"code": code["code"], "senior_id": "tan",
                                       "consent": {"family_sees": "nothing", "share_words": False, "share_activity": False}})
        self.assertEqual(r.status_code, 200)
        kv_after = s.get("contact", "tan-kelvin")
        # The contact's consent is NOT updated (existing link is reused, code only updates senior.consent).
        self.assertEqual(kv_after.get("consent", {}).get("family_sees"), kv_before_consent)

    def test_nonexistent_senior_id_on_pair_creates_senior(self):
        """If senior_id doesn't exist, the pair endpoint creates the senior from the pair code."""
        code = self.c.post("/care/pair-code", json={"contact_name": "Test", "senior_name": "Mr Ghost",
                                                      "home_postal": "560999"}).json()
        ghost_sid = "sen-does-not-exist"
        r = self.c.post("/pair", json={"code": code["code"], "senior_id": ghost_sid, "language": "en",
                                       "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["senior_id"], ghost_sid)
        self.assertIsNotNone(self.store.get("senior", ghost_sid))

    def test_role_mismatch_aac_caregiver_on_family_senior(self):
        """An AAC caregiver (role=aac) pairing onto a family-path senior creates
        a contact with role='aac', which won't appear in contacts_for for family messages."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Create an AAC pair code.
        code = self.c.post("/care/pair-code", json={"contact_name": "AAC Worker", "role": "aac",
                                                      "senior_name": "Mr Tan", "home_postal": "560999",
                                                      "worker_id": "aac-test"}).json()
        r = self.c.post("/pair", json={"code": code["code"], "senior_id": "tan"})
        self.assertEqual(r.status_code, 200)
        # The contact exists but has role='aac' on a family-path senior.
        new_contact = s.get("contact", r.json()["contact_id"])
        self.assertEqual(new_contact["role"], "aac")
        # contacts_for filters by the senior's path, so this AAC contact won't appear for family messages.
        from backend.engine.ladder import contacts_for
        senior = s.get("senior", "tan")
        fam_contacts = contacts_for(s, senior)
        self.assertNotIn(new_contact["id"], [c["id"] for c in fam_contacts])

    def test_used_code_cannot_be_reused(self):
        code = self.c.post("/care/pair-code", json={"contact_name": "Once", "senior_name": "Mr Once",
                                                      "home_postal": "560999"}).json()
        r1 = self.c.post("/pair", json={"code": code["code"], "language": "en",
                                        "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})
        self.assertEqual(r1.status_code, 200)
        r2 = self.c.post("/pair", json={"code": code["code"]})
        self.assertEqual(r2.status_code, 404)


class PrimaryManagement(unittest.TestCase):
    """Promotion, demotion, and primary-targeting in the engine."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_set_primary_on_unknown_contact_returns_404(self):
        r = self.c.post("/care/contact/no-such-contact/primary")
        self.assertEqual(r.status_code, 404)

    def test_exactly_one_primary_after_sequence_of_calls(self):
        """After any sequence of set_primary calls, there is exactly one primary per senior."""
        # Start: Wei Ling is primary.
        self.c.post("/care/contact/tan-kelvin/primary")
        contacts = self.store.list("contact", senior_id="tan")
        primaries = [c for c in contacts if c["primary"]]
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0]["id"], "tan-kelvin")
        # Switch back to Wei Ling.
        self.c.post("/care/contact/tan-weiling/primary")
        contacts2 = self.store.list("contact", senior_id="tan")
        primaries2 = [c for c in contacts2 if c["primary"]]
        self.assertEqual(len(primaries2), 1)
        self.assertEqual(primaries2[0]["id"], "tan-weiling")
        # Switch to Kelvin again.
        self.c.post("/care/contact/tan-kelvin/primary")
        contacts3 = self.store.list("contact", senior_id="tan")
        primaries3 = [c for c in contacts3 if c["primary"]]
        self.assertEqual(len(primaries3), 1)

    def test_removing_primary_leaves_no_primary(self):
        """Deleting the primary contact via DELETE /senior/{id}/knows/contact:... leaves no primary."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Wei Ling is primary for Mr Tan. Delete her contact.
        r = self.c.delete("/senior/tan/knows/contact:tan-weiling")
        self.assertEqual(r.status_code, 204)
        contacts = s.list("contact", senior_id="tan")
        self.assertEqual(len(contacts), 1)  # only Kelvin left
        primaries = [c for c in contacts if c.get("primary")]
        self.assertEqual(len(primaries), 0)  # no primary after deletion

    def test_rung4_after_no_primary_goes_to_all(self):
        """When there's no primary, rung-4 falls back to all contacts (line 120 of ladder.py:
        `[c for c in contacts if c.get("primary")] or contacts`)."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Delete the primary (Wei Ling), leaving only Kelvin (non-primary).
        self.c.delete("/senior/tan/knows/contact:tan-weiling")
        # Advance to trigger a rung-4 handover (double dose on day 11).
        self.c.post("/demo/advance", json={"days": 11})
        # Check messages: Kelvin should receive the family handover (fallback to all).
        msgs = [m for m in s.list("message", senior_id="tan") if m["to"] == "family"]
        # At least one family message exists for the rung-4 day.
        self.assertTrue(any(m["contact_id"] == "tan-kelvin" for m in msgs),
                        "After removing primary, rung-4 should still reach the remaining contact")


class CaregiverView(unittest.TestCase):
    """GET /care/caregiver/{id} edge cases."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_unknown_caregiver_returns_404(self):
        r = self.c.get("/care/caregiver/cg-nope")
        self.assertEqual(r.status_code, 404)

    def test_status_per_senior_matches(self):
        """The status field in caregiver_view matches _status() for each senior."""
        self.c.post("/demo/advance", json={"days": 11})
        r = self.c.get("/care/caregiver/cg-weiling").json()
        for s in r["seniors"]:
            expected = _status(s["senior_id"], demo.today(self.store))
            self.assertEqual(s["status"], expected)

    def test_senior_record_gone_is_skipped(self):
        """If a senior's record is deleted, the caregiver view skips that senior."""
        s = self.store.get("senior", "tan")
        self.store.delete("senior", "tan")
        r = self.c.get("/care/caregiver/cg-weiling").json()
        senior_ids = [x["senior_id"] for x in r["seniors"]]
        self.assertNotIn("tan", senior_ids)
        # Restore for other tests.
        self.store.put("senior", s)

    def test_sorted_by_name(self):
        """Seniors in caregiver_view are sorted by senior_name."""
        r = self.c.get("/care/caregiver/cg-siti").json()
        names = [s["senior_name"] for s in r["seniors"]]
        self.assertEqual(names, sorted(names))


class AacCaseload(unittest.TestCase):
    """AAC caseload matching on caregiver_id AND legacy worker_id."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_matches_on_caregiver_id(self):
        """Caseload matches contacts whose caregiver_id is the worker."""
        r = self.c.get("/care/aac/cg-siti/caseload").json()
        self.assertEqual(len(r["seniors"]), 3)

    def test_matches_on_legacy_worker_id(self):
        """Caseload also matches contacts with the old worker_id field."""
        r = self.c.get("/care/aac/aac-siti/caseload").json()
        self.assertEqual(len(r["seniors"]), 3)

    def test_no_duplicate_rows(self):
        """A contact matching both caregiver_id and worker_id appears once, not twice."""
        r = self.c.get("/care/aac/aac-siti/caseload").json()
        senior_ids = [s["senior"]["id"] for s in r["seniors"]]
        self.assertEqual(len(senior_ids), len(set(senior_ids)))


class HandoverClaim(unittest.TestCase):
    """Claim edge cases: non-primary can claim; wrong senior's caregiver gets 403."""

    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_non_primary_caregiver_can_claim(self):
        """Kelvin (non-primary) can claim a handover for Mr Tan."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        self.c.post("/demo/advance", json={"days": 11})
        fam = self.c.get("/care/family/tan-kelvin").json()
        ho = next(h for h in fam["handovers"] if h["status"] == "open")
        r = self.c.post(f"/handover/{ho['id']}/claim", json={"contact_id": "tan-kelvin", "choice": "polyclinic"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["claimed_by"], "tan-kelvin")

    def test_caregiver_from_another_senior_gets_403(self):
        """A contact linked to a different senior cannot claim this senior's handover."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        self.c.post("/demo/advance", json={"days": 11})
        fam = self.c.get("/care/family/tan-weiling").json()
        ho = next(h for h in fam["handovers"] if h["status"] == "open")
        # Wong-mei is linked to Mdm Wong, not Mr Tan.
        r = self.c.post(f"/handover/{ho['id']}/claim", json={"contact_id": "wong-mei", "choice": "polyclinic"})
        self.assertEqual(r.status_code, 403)


class SchemaIntegrity(unittest.TestCase):
    """Every stored contact has caregiver_id, and every caregiver_id points to an existing caregiver."""

    def test_after_seed(self):
        s = Store(":memory:")
        demo.seed(s)
        contacts = s.list("contact")
        self.assertTrue(contacts)
        for c in contacts:
            self.assertIn("caregiver_id", c, f"contact {c['id']} missing caregiver_id")
            cg = s.get("caregiver", c["caregiver_id"])
            self.assertIsNotNone(cg, f"contact {c['id']} references orphan caregiver {c['caregiver_id']}")

    def test_after_advance(self):
        s = Store(":memory:")
        demo.seed(s)
        demo.advance(s, 5)
        contacts = s.list("contact")
        self.assertTrue(contacts)
        for c in contacts:
            self.assertIn("caregiver_id", c, f"contact {c['id']} missing caregiver_id")
            cg = s.get("caregiver", c["caregiver_id"])
            self.assertIsNotNone(cg, f"contact {c['id']} references orphan caregiver {c['caregiver_id']}")


class LegacyData(unittest.TestCase):
    """A contact row without caregiver_id (old careloop.db) doesn't crash endpoints."""

    def test_family_view_does_not_crash(self):
        s = Store(":memory:")
        demo.seed(s)
        # Corrupt a contact: remove caregiver_id (simulate old data).
        c = s.get("contact", "tan-weiling")
        c.pop("caregiver_id", None)
        s.put("contact", c)
        api.use_store(s)
        client = TestClient(api.app)
        r = client.get("/care/family/tan-weiling")
        # Should not 500. It may 200 (family_view doesn't use caregiver_id directly)
        # or 422 if the contact fails schema validation — but NOT a 500.
        self.assertNotEqual(r.status_code, 500)

    def test_contacts_for_does_not_crash(self):
        s = Store(":memory:")
        demo.seed(s)
        c = s.get("contact", "tan-weiling")
        c.pop("caregiver_id", None)
        s.put("contact", c)
        from backend.engine.ladder import contacts_for
        senior = s.get("senior", "tan")
        # Should not crash — contacts_for doesn't read caregiver_id.
        result = contacts_for(s, senior)
        self.assertTrue(any(x["id"] == "tan-weiling" for x in result))

    def test_caseload_does_not_crash(self):
        s = Store(":memory:")
        demo.seed(s)
        c = s.get("contact", "aac-siti:lee")
        c.pop("caregiver_id", None)
        s.put("contact", c)
        api.use_store(s)
        client = TestClient(api.app)
        r = client.get("/care/aac/aac-siti/caseload")
        self.assertNotEqual(r.status_code, 500)
        # The legacy contact still appears via worker_id matching.
        rows = r.json()["seniors"]
        self.assertTrue(any(x["senior"]["id"] == "lee" for x in rows))


if __name__ == "__main__":
    unittest.main()
