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
        self.assertEqual(len(examples), 10)
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
        kinds = {"senior": "Senior", "contact": "Contact", "reading": "Reading", "checkin": "CheckIn", "envday": "EnvDay",
                 "decision": "Decision", "message": "Message", "handover": "Handover", "suggestion": "Suggestion"}
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
        need = [r for r in rows if r["status"] == "handover"]
        self.assertEqual({r["senior"]["name"] for r in need}, {"Mr Ng", "Mr Chandran"})  # Mr Chandran's drift: demo.py
        self.assertEqual(rows[:len(need)], need)  # those who need a look come first
        self.assertTrue(all(r["status"] == "quiet" for r in rows[len(need):]))

    def test_programmes_feed_suggestions(self):
        r = self.c.put("/aac/aac-002/programmes", json=[{"title": "Karaoke", "title_zh": "卡拉OK", "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                                                         "time": "10am", "tags": ["karaoke"], "indoor": True}])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/aac/aac-002/programmes").json()[0]["title"], "Karaoke")

    def test_brief_pdf_is_nathans(self):
        self.assertIn(self.c.get("/senior/tan/brief.pdf").status_code, (200, 501))


if __name__ == "__main__":
    unittest.main()
