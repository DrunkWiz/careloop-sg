"""Medicine notes stay explanation, never advice; unknown medicines are never guessed; the staying-well checklist
picks the right items and knows what's due."""
import re
import unittest
from datetime import date

from backend.language.guardrail import RULES
from backend.reports.medicines import ALWAYS, TABLE, UNKNOWN, explain, explain_all, identify
from backend.reports.prevention import ITEMS, checklist

TODAY = date(2026, 10, 24)
SENIOR = {"id": "s1", "language": "en", "conditions": ["hypertension"],
          "medicines": [{"name": "amlodipine", "dose_text": "5 mg once a day", "schedule": ["morning"], "started": "2024-03-01", "for_bp": True}]}


def all_texts():
    for generic, e in TABLE.items():
        for lang in ("en", "zh"):
            what, how, look = e[lang]
            yield generic, lang, [what, how, *look]
    yield "always", "both", list(ALWAYS.values()) + list(UNKNOWN.values())


class MedicineNotes(unittest.TestCase):
    def test_no_advice_in_any_note(self):
        """The same rules the guardrail applies to messages: no diagnosis, no dose change, no stop or skip."""
        for name, lang, texts in all_texts():
            for text in texts:
                for rule in ("diagnosis", "dose_change", "stop_medicine"):
                    for pattern in RULES[rule]:
                        with self.subTest(name=name, lang=lang, rule=rule, text=text):
                            self.assertIsNone(re.search(pattern, text.lower()), pattern)

    def test_every_entry_has_both_languages(self):
        for generic, e in TABLE.items():
            with self.subTest(generic):
                self.assertTrue(all(e["en"][:2]) and all(e["zh"][:2]))
                self.assertEqual(len(e["en"][2]), len(e["zh"][2]))

    def test_names_match_exactly_or_by_brand(self):
        self.assertEqual(identify("Amlodipine 5mg tablet"), "amlodipine")
        self.assertEqual(identify("NORVASC"), "amlodipine")
        self.assertEqual(identify("Lipitor 20 mg"), "atorvastatin")
        self.assertIsNone(identify("amlo"))  # never "close enough"
        self.assertIsNone(identify("Zanidip"))

    def test_unknown_medicine_says_so(self):
        m = explain({"name": "Zanidip", "dose_text": "10 mg once a day", "schedule": ["morning"], "for_bp": True})
        self.assertFalse(m["known"])
        self.assertIn("pharmacist", m["what_for"])
        self.assertEqual(m["look_out_for"], [])
        self.assertEqual(m["dose_text"], "10 mg once a day")  # the label, as it is

    def test_language(self):
        zh = explain_all({**SENIOR, "language": "zh"})
        self.assertEqual(zh["medicines"][0]["what_for"], "降血压。")
        self.assertEqual(zh["medicines"][0]["when"], ["早上"])
        self.assertEqual(explain_all({**SENIOR, "language": "en-SG"})["medicines"][0]["what_for"], "Lowers blood pressure.")


class StayingWell(unittest.TestCase):
    def ids(self, senior, notes=None):
        return {i["id"]: i for i in checklist(senior, TODAY, notes)["items"]}

    def test_diabetes_items_only_with_diabetes(self):
        plain = self.ids(SENIOR)
        self.assertNotIn("diabetes_eye", plain)
        self.assertIn("cardio_screen", plain)
        dm = self.ids({**SENIOR, "medicines": SENIOR["medicines"] + [{"name": "metformin", "dose_text": "", "schedule": [], "for_bp": False}]})
        self.assertIn("diabetes_eye", dm)
        self.assertIn("med_review", dm)
        self.assertNotIn("cardio_screen", dm)  # diabetes is already known; it's monitored, not screened for

    def test_due_done_and_not_recorded(self):
        items = self.ids(SENIOR, {"prevention": {"flu": "2025-10-01", "pneumococcal": "2024-01-01", "covid": "2026-09-30"}})
        self.assertEqual(items["flu"]["status"], "due")
        self.assertEqual(items["pneumococcal"]["status"], "done")  # once is enough
        self.assertEqual(items["covid"]["status"], "done")
        self.assertEqual(items["covid"]["next_due"], "2027-09-30")
        self.assertEqual(items["fit"]["status"], "not_recorded")

    def test_an_upcoming_visit_books_the_bp_review(self):
        items = self.ids(SENIOR, {"appointments": [{"date": "2026-10-29"}]})
        self.assertEqual((items["bp_review"]["status"], items["bp_review"]["next_due"]), ("booked", "2026-10-29"))

    def test_due_first_and_both_languages(self):
        items = checklist({**SENIOR, "language": "zh"}, TODAY, {"prevention": {"flu": "2025-01-01"}})["items"]
        self.assertEqual(items[0]["id"], "flu")
        self.assertEqual(items[0]["status_text"], "该做了")
        for _, _, _, _, en, zh in ITEMS:
            self.assertTrue(all(en) and all(zh))


if __name__ == "__main__":
    unittest.main()
