"""API against the contract: every endpoint, every object validated against contracts/schemas."""
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from backend.api import app as api
from backend.api import demo
from backend.api.store import Store

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
SCHEMAS = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (CONTRACTS / "schemas").glob("*.schema.json")}
REGISTRY = Registry().with_resources((name, Resource.from_contents(s)) for name, s in SCHEMAS.items())


def validate(name: str, doc: dict) -> None:
    Draft202012Validator(SCHEMAS[f"{name}.schema.json"], registry=REGISTRY, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(doc)


class Contract(unittest.TestCase):
    def test_every_example_validates(self):
        examples = list((CONTRACTS / "examples").glob("*.json"))
        self.assertEqual(len(examples), 13)
        for p in examples:
            with self.subTest(p.name):
                validate(p.stem, json.loads(p.read_text(encoding="utf-8")))


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(":memory:")
        api.use_store(cls.store)
        demo.seed(cls.store)
        cls.c = TestClient(api.app)

    def setUp(self):
        api.use_store(self.store)

    def test_meta(self):
        m = self.c.get("/meta").json()
        self.assertEqual(m["model_chain"][-1], "rules+templates")
        self.assertEqual(m["data_sources"]["people"], "synthetic")

    def test_every_stored_object_matches_its_schema(self):
        kinds = {"senior": "Senior", "contact": "Contact", "caregiver": "Caregiver", "reading": "Reading", "checkin": "CheckIn", "envday": "EnvDay",
                 "decision": "Decision", "message": "Message", "handover": "Handover", "suggestion": "Suggestion", "ventpost": "VentPost", "rota": "Rota"}
        self.c.post("/demo/advance", json={"days": 3})
        for kind, schema in kinds.items():
            docs = self.store.list(kind)
            for doc in docs[:: max(1, len(docs) // 25)]:
                with self.subTest(kind=kind, id=doc["id"]):
                    validate(schema, doc)

    def test_checkin_red_flag_answers_immediately(self):
        r = self.c.post("/checkin", json={"senior_id": "wong", "text": "今天胸口有点痛", "source": "voice"}).json()
        self.assertEqual(r["rung"], "R")
        validate("Message", r["message"])
        self.assertIn("995", r["message"]["text"])
        fam = self.c.get("/care/family/wong-mei").json()
        self.assertEqual(fam["status"], "red_flag")

    def test_checkin_low_confidence_number_is_not_used(self):
        r = self.c.post("/checkin", json={"senior_id": "lee", "text": "BP today 145 90", "source": "voice"}).json()
        self.assertTrue(r["facts"]["bp"][0]["needs_confirmation"])
        r2 = self.c.post("/reading", json={"senior_id": "lee", "kind": "bp", "values": {"systolic": 145, "diastolic": 90}, "source": "voice"}).json()
        self.assertTrue(r2["reading"]["trust"]["ok"])

    def test_reading_trust_flags(self):
        r = self.c.post("/reading", json={"senior_id": "goh", "kind": "glucose", "values": {"value": 7.2, "unit": "mg/dL"}}).json()
        self.assertEqual(r["reading"]["trust"]["flags"], ["units"])

    def test_today(self):
        t = self.c.get("/senior/tan/today").json()
        self.assertLessEqual(len(t["suggestions"]), 3)
        for s in t["suggestions"]:
            validate("Suggestion", s)
        self.assertIn(t["haze"] and t["haze"]["band"], (None, "unhealthy", "very_unhealthy", "hazardous", "good"))

    def test_not_for_me_is_remembered(self):
        t = self.c.get("/senior/wong/today").json()
        sug = t["suggestions"][0]
        self.c.post(f"/senior/wong/suggestions/{sug['id']}/response", json={"response": "not_for_me"})
        self.assertIn(sug["place_id"], self.store.get("senior", "wong")["hidden_suggestions"])
        self.assertNotIn(sug["id"], [s["id"] for s in self.c.get("/senior/wong/today").json()["suggestions"]])

    def test_knows_and_erase(self):
        k = self.c.get("/senior/goh/knows").json()
        like = next(x for x in k if x["kind"] == "like")
        self.assertEqual(self.c.delete(f"/senior/goh/knows/{like['id']}").status_code, 204)
        self.assertNotIn(like["id"], [x["id"] for x in self.c.get("/senior/goh/knows").json()])

    def test_pairing(self):
        code = self.c.post("/care/pair-code", json={"contact_name": "Daughter", "senior_name": "Mdm Tay", "home_postal": "640999"}).json()
        r = self.c.post("/pair", json={"code": code["code"], "language": "zh",
                                       "consent": {"family_sees": "digest", "share_words": False, "share_activity": True}})
        self.assertEqual(r.status_code, 200)
        sid = r.json()["senior_id"]
        validate("Senior", self.store.get("senior", sid))
        self.assertEqual(self.store.get("senior", sid)["region"], "west")
        self.assertEqual(self.c.post("/pair", json={"code": code["code"]}).status_code, 404)  # one use

    def test_handover_claim_flow(self):
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        self.c.post("/demo/advance", json={"days": 11})
        fam = self.c.get("/care/family/tan-weiling").json()
        ho = next(h for h in fam["handovers"] if h["status"] == "open")
        self.assertEqual(self.c.post(f"/handover/{ho['id']}/claim", json={"contact_id": "tan-weiling", "choice": "just handle it"}).status_code, 400)
        r = self.c.post(f"/handover/{ho['id']}/claim", json={"contact_id": "tan-weiling", "choice": "polyclinic"}).json()
        self.assertEqual((r["status"], r["claimed_by"]), ("claimed", "tan-weiling"))
        # The second family member sees who did.
        kelvin = self.c.get("/care/family/tan-kelvin").json()
        self.assertEqual(next(h for h in kelvin["handovers"] if h["id"] == ho["id"])["claimed_by_name"], "Wei Ling")
        brief = self.c.get("/senior/tan/brief.json").json()
        self.assertTrue(any(e["rung"] == "4" for e in brief["events"]))
        self.assertEqual(len(brief["bp_daily"]), 90)

    def test_aac_caseload_sorted_by_need(self):
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        self.c.post("/demo/advance", json={"days": 14})
        rows = self.c.get("/care/aac/aac-siti/caseload").json()["seniors"]
        self.assertEqual(rows[0]["senior"]["name"], "Mr Ng")
        self.assertEqual(rows[0]["status"], "handover")
        self.assertTrue(all(r["status"] == "quiet" for r in rows[1:]))

    def test_programmes_feed_suggestions(self):
        r = self.c.put("/aac/aac-002/programmes", json=[{"title": "Karaoke", "title_zh": "卡拉OK", "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                                                         "time": "10am", "tags": ["karaoke"], "indoor": True}])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/aac/aac-002/programmes").json()[0]["title"], "Karaoke")

    def test_two_caregivers_on_one_senior(self):
        """Mr Tan has two caregivers: Wei Ling (primary) and Kelvin."""
        contacts = self.store.list("contact", senior_id="tan")
        self.assertEqual(len(contacts), 2)
        primaries = [c for c in contacts if c.get("primary")]
        self.assertEqual(len(primaries), 1)
        self.assertEqual(primaries[0]["id"], "tan-weiling")
        # Both can see the family view; each sees the other in other_contacts.
        wl = self.c.get("/care/family/tan-weiling").json()
        self.assertEqual(wl["senior"]["name"], "Mr Tan")
        self.assertEqual(len(wl["other_contacts"]), 1)
        self.assertEqual(wl["other_contacts"][0]["name"], "Kelvin")
        kv = self.c.get("/care/family/tan-kelvin").json()
        self.assertEqual(len(kv["other_contacts"]), 1)
        self.assertEqual(kv["other_contacts"][0]["name"], "Wei Ling")
        # The caregiver view lists one senior for each.
        cg_wl = self.c.get("/care/caregiver/cg-weiling").json()
        self.assertEqual(cg_wl["caregiver"]["name"], "Wei Ling")
        self.assertEqual(len(cg_wl["seniors"]), 1)
        self.assertTrue(cg_wl["seniors"][0]["primary"])
        cg_kv = self.c.get("/care/caregiver/cg-kelvin").json()
        self.assertEqual(cg_kv["caregiver"]["name"], "Kelvin")
        # Kelvin also looks after his mother (Mrs Yeo, primary). The two-senior view should be sorted by name.
        self.assertEqual(len(cg_kv["seniors"]), 2)
        self.assertEqual(cg_kv["seniors"][0]["senior_name"], "Mr Tan")
        self.assertFalse(cg_kv["seniors"][0]["primary"])
        self.assertEqual(cg_kv["seniors"][1]["senior_name"], "Mrs Yeo")
        self.assertTrue(cg_kv["seniors"][1]["primary"])

    def test_one_caregiver_two_seniors(self):
        """Siti is the AAC caregiver for Lee, Goh, and Ng — three seniors."""
        r = self.c.get("/care/caregiver/cg-siti").json()
        self.assertEqual(r["caregiver"]["name"], "Siti")
        self.assertEqual(r["caregiver"]["role"], "aac")
        senior_names = {s["senior_name"] for s in r["seniors"]}
        self.assertEqual(senior_names, {"Mdm Lee", "Mr Goh", "Mr Ng"})
        # Each senior has a distinct contact_id.
        contact_ids = [s["contact_id"] for s in r["seniors"]]
        self.assertEqual(len(contact_ids), len(set(contact_ids)))

    def test_duplicate_pairing_not_created(self):
        """Pairing the same caregiver to the same senior twice reuses the contact, no duplicate."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Kelvin is already linked to Mr Tan (tan-kelvin). Create a new code for the same caregiver.
        code1 = self.c.post("/care/pair-code", json={"caregiver_id": "cg-kelvin", "contact_name": "Kelvin",
                                                      "senior_name": "Mr Tan", "home_postal": "560999"}).json()
        before = len(s.list("contact", senior_id="tan"))
        r = self.c.post("/pair", json={"code": code1["code"], "senior_id": "tan",
                                       "consent": {"family_sees": "digest", "share_words": False, "share_activity": True}})
        self.assertEqual(r.status_code, 200)
        after = len(s.list("contact", senior_id="tan"))
        self.assertEqual(before, after)  # no new contact created
        # The existing contact is reused.
        self.assertEqual(r.json()["contact_id"], "tan-kelvin")
        # A second code for the same pair: still no duplicate.
        code2 = self.c.post("/care/pair-code", json={"caregiver_id": "cg-kelvin", "contact_name": "Kelvin",
                                                      "senior_name": "Mr Tan", "home_postal": "560999"}).json()
        r2 = self.c.post("/pair", json={"code": code2["code"], "senior_id": "tan"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(s.list("contact", senior_id="tan")), after)

    def test_set_primary_caregiver(self):
        """POST /care/contact/{id}/primary promotes a non-primary contact and demotes the old one."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        before = {c["id"]: c.get("primary", False) for c in s.list("contact", senior_id="tan")}
        self.assertTrue(before["tan-weiling"])
        self.assertFalse(before["tan-kelvin"])
        r = self.c.post("/care/contact/tan-kelvin/primary")
        self.assertEqual(r.status_code, 200)
        after = {c["id"]: c.get("primary", False) for c in s.list("contact", senior_id="tan")}
        self.assertFalse(after["tan-weiling"])
        self.assertTrue(after["tan-kelvin"])

    # --- AAC centre on pairing -----------------------------------------------

    def _pair_aac(self, s, **extra):
        code = self.c.post("/care/pair-code", json={"role": "aac", "contact_name": "x", "senior_name": "Mdm New",
                                                    "home_postal": "520888", **extra})
        return code

    def test_aac_pairing_uses_workers_usual_centre(self):
        """A senior paired by Siti joins aac-105, the centre her other seniors belong to."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        code = self._pair_aac(s, caregiver_id="cg-siti").json()
        r = self.c.post("/pair", json={"code": code["code"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(s.get("senior", r.json()["senior_id"])["aac_id"], "aac-105")

    def test_aac_pairing_explicit_centre(self):
        """An explicit aac_id wins over the worker's usual centre."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        code = self._pair_aac(s, caregiver_id="cg-siti", aac_id="aac-002").json()
        r = self.c.post("/pair", json={"code": code["code"]})
        self.assertEqual(s.get("senior", r.json()["senior_id"])["aac_id"], "aac-002")

    def test_aac_pairing_unknown_centre_rejected(self):
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        self.assertEqual(self._pair_aac(s, caregiver_id="cg-siti", aac_id="aac-nope").status_code, 400)

    def test_aac_pairing_new_worker_no_centre(self):
        """A brand-new AAC worker with no seniors and no aac_id: the centre stays empty, nothing crashes."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        code = self._pair_aac(s).json()
        r = self.c.post("/pair", json={"code": code["code"]})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(s.get("senior", r.json()["senior_id"])["aac_id"])

    def test_family_pairing_never_sets_centre(self):
        """aac_id is ignored on the family path."""
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        code = self.c.post("/care/pair-code", json={"role": "family", "contact_name": "Ah Boy", "aac_id": "aac-105",
                                                    "senior_name": "Mr New", "home_postal": "560888"}).json()
        r = self.c.post("/pair", json={"code": code["code"]})
        self.assertIsNone(s.get("senior", r.json()["senior_id"])["aac_id"])

    def test_aac_pairing_fills_centre_on_existing_senior_only_if_empty(self):
        s = Store(":memory:")
        api.use_store(s)
        demo.seed(s)
        # Mdm Wong already has aac-002: an AAC link must not move her.
        code = self._pair_aac(s, caregiver_id="cg-siti", senior_id="wong").json()
        self.c.post("/pair", json={"code": code["code"], "senior_id": "wong"})
        self.assertEqual(s.get("senior", "wong")["aac_id"], "aac-002")
        # A senior with no centre picks one up.
        w = s.get("senior", "tan")
        w["aac_id"] = None
        s.put("senior", w)
        code = self._pair_aac(s, caregiver_id="cg-siti", senior_id="tan").json()
        self.c.post("/pair", json={"code": code["code"], "senior_id": "tan"})
        self.assertEqual(s.get("senior", "tan")["aac_id"], "aac-105")

    def test_today_follows_app_language(self):
        """?lang= picks the language of the haze card (and prompt); default is the senior's saved one."""
        s = Store(":memory:")  # fresh: other tests move the demo clock past the haze day
        api.use_store(s)
        demo.seed(s)
        en = self.c.get("/senior/tan/today").json()
        zh = self.c.get("/senior/tan/today?lang=zh").json()
        self.assertIsNotNone(en["haze"])
        self.assertRegex(zh["haze"]["text"], r"[\u4e00-\u9fff]")
        self.assertNotRegex(en["haze"]["text"], r"[\u4e00-\u9fff]")
        if zh["prompt"]:
            self.assertEqual(zh["prompt"]["language"], "zh")
        # Tamil and Malay are UI-only: the server never accepts them.
        self.assertEqual(self.c.get("/senior/tan/today?lang=ta").status_code, 422)

    def test_brief_pdf_is_nathans(self):
        self.assertIn(self.c.get("/senior/tan/brief.pdf").status_code, (200, 501))

    # --- vent space -----------------------------------------------------------

    def test_vent_post_and_feed(self):
        """Posting creates a vent post; the feed returns it newest-first."""
        r = self.c.post("/vent", json={"nickname": "Caregiver 001", "text": "So tired today"})
        self.assertEqual(r.status_code, 200)
        post = r.json()
        self.assertEqual(post["nickname"], "Caregiver 001")
        self.assertEqual(post["text"], "So tired today")
        self.assertEqual(post["hugs"], 0)
        self.assertFalse(post["hidden"])
        self.assertIn("id", post)
        self.assertIn("time", post)
        validate("VentPost", post)
        # Feed returns visible posts, newest first.
        feed = self.c.get("/vent").json()
        self.assertGreater(len(feed), 0)
        self.assertEqual(feed[0]["id"], post["id"])

    def test_vent_strips_phone_nric_postal(self):
        """Phone numbers, NRIC-style numbers and postal codes are replaced with [removed]."""
        text = "Call me at 9123 4567. NRIC S1234567D. Postal 560999."
        r = self.c.post("/vent", json={"nickname": "Anon", "text": text})
        self.assertEqual(r.status_code, 200)
        cleaned = r.json()["text"]
        self.assertNotIn("9123 4567", cleaned)
        self.assertNotIn("S1234567D", cleaned)
        self.assertNotIn("560999", cleaned)
        self.assertIn("[removed]", cleaned)

    def test_vent_hug_increments_count(self):
        """POST /vent/{id}/hug increments the hug count."""
        r = self.c.post("/vent", json={"nickname": "Caregiver 042", "text": "Hard day"})
        pid = r.json()["id"]
        self.assertEqual(r.json()["hugs"], 0)
        h1 = self.c.post(f"/vent/{pid}/hug").json()
        self.assertEqual(h1["hugs"], 1)
        h2 = self.c.post(f"/vent/{pid}/hug").json()
        self.assertEqual(h2["hugs"], 2)

    def test_vent_report_hides_post(self):
        """POST /vent/{id}/report sets hidden=True, so it disappears from the feed."""
        r = self.c.post("/vent", json={"nickname": "Anon", "text": "test post for report"})
        pid = r.json()["id"]
        # Visible before reporting.
        ids = [p["id"] for p in self.c.get("/vent").json()]
        self.assertIn(pid, ids)
        # Report it.
        rep = self.c.post(f"/vent/{pid}/report").json()
        self.assertTrue(rep["hidden"])
        # No longer in the feed.
        ids_after = [p["id"] for p in self.c.get("/vent").json()]
        self.assertNotIn(pid, ids_after)
        # The stored post is hidden.
        self.assertTrue(self.store.get("ventpost", pid)["hidden"])

    def test_vent_old_posts_not_returned(self):
        """Posts older than 7 days are excluded from the feed."""
        from datetime import timedelta
        from backend.api.app import now
        # Insert a post dated 8 days ago directly into the store.
        old_time = (now() - timedelta(days=8)).isoformat()
        self.store.put("ventpost", {
            "id": "vp-old-test", "nickname": "Old Timer", "text": "stale post",
            "time": old_time, "hugs": 0, "hidden": False,
        })
        feed = self.c.get("/vent").json()
        ids = [p["id"] for p in feed]
        self.assertNotIn("vp-old-test", ids)
        # A fresh post (2 hours ago) IS returned.
        fresh_time = (now() - timedelta(hours=2)).isoformat()
        self.store.put("ventpost", {
            "id": "vp-fresh-test", "nickname": "Fresh", "text": "recent post",
            "time": fresh_time, "hugs": 0, "hidden": False,
        })
        feed2 = self.c.get("/vent").json()
        ids2 = [p["id"] for p in feed2]
        self.assertIn("vp-fresh-test", ids2)

    def test_vent_no_caregiver_or_senior_id_saved(self):
        """No caregiver_id or senior_id is stored on a vent post."""
        r = self.c.post("/vent", json={"nickname": "Anon", "text": "just venting"})
        pid = r.json()["id"]
        stored = self.store.get("ventpost", pid)
        self.assertNotIn("caregiver_id", stored)
        self.assertNotIn("senior_id", stored)


if __name__ == "__main__":
    unittest.main()
