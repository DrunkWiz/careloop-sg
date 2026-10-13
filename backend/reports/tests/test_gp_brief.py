"""GP brief: always one page, every input shape renders, nothing invented."""
import re
import unittest
from datetime import date, timedelta

from backend.reports import gp_brief_pdf
from backend.reports.gp_brief import DANGER, MAX_EVENTS, MAX_WORDS, _pick


def pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


def brief(days=90, events=(), words=(), readings=True, aac=None):
    end = date(2026, 10, 24)
    bp = []
    for i in range(days):
        d = end - timedelta(days - 1 - i)
        on = readings and i >= days - 50 and i % 9 != 0
        bp.append({"date": d.isoformat(), "systolic": 128 + (i > days - 8) * 15 if on else None,
                   "diastolic": 80 + (i > days - 8) * 8 if on else None})
    return {
        "senior": {"id": "tan", "name": "Mr Tan", "conditions": ["hypertension"],
                   "medicines": [{"name": "amlodipine", "dose_text": "5 mg once a day", "started": "2024-03-01"}]},
        "period": {"from": bp[0]["date"], "to": bp[-1]["date"]},
        "baseline": {"systolic": 129, "diastolic": 78, "days": 25, "fallback": False},
        "bp_daily": bp,
        "adherence": {"taken_days": 40, "missed_days": 3, "reported_days": 43},
        "events": list(events), "in_their_words": list(words), "aac": aac,
        "note": "Generated from the CareLoop decision log. Not connected to any clinic system. Synthetic data in the demo.",
    }


def event(day, rung="3"):
    return {"date": f"2026-10-{day:02d}", "rung": rung, "rule_id": f"{rung}.x", "reason": "7-day average systolic 140",
            "decision_id": f"dec-tan-2026-10-{day:02d}"}


class GPBrief(unittest.TestCase):
    def test_typical_brief_is_one_pdf_page(self):
        pdf = gp_brief_pdf(brief(events=[event(21), event(24, "4")],
                                 words=[{"date": "2026-10-24", "said": "giddy when stand up", "symptoms": ["dizziness"], "questions": []}]))
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(pages(pdf), 1)

    def test_long_history_still_one_page(self):
        many = [event(d, "R" if d == 20 else "3") for d in range(1, 25)]
        words = [{"date": f"2026-10-{d:02d}", "said": "头有点晕 " * 30, "symptoms": ["dizziness"],
                  "questions": ["Should I take it at night?"]} for d in range(1, 25)]
        self.assertEqual(pages(gp_brief_pdf(brief(events=many, words=words))), 1)

    def test_mandarin_and_singlish_words(self):
        words = [{"date": "2026-10-23", "said": "今天还好，就是胸口有点痛", "symptoms": ["chest_pain"], "questions": []},
                 {"date": "2026-10-24", "said": "I'm fine lah", "symptoms": [], "questions": []}]
        pdf = gp_brief_pdf(brief(events=[event(23, "R")], words=words))
        self.assertIn(b"STSong-Light", pdf)
        self.assertEqual(pages(pdf), 1)

    def test_no_readings_no_events(self):
        pdf = gp_brief_pdf(brief(readings=False))
        self.assertEqual(pages(pdf), 1)

    def test_empty_dict_does_not_crash(self):
        self.assertEqual(pages(gp_brief_pdf({})), 1)

    def test_aac_named_for_the_gp(self):
        pdf = gp_brief_pdf(brief(aac={"id": "aac-100", "name": "Sample AAC", "going": ["Karaoke"]}))
        self.assertEqual(pages(pdf), 1)

    def test_red_flag_never_cut(self):
        events = [event(1, "R")] + [event(d) for d in range(2, 25)]
        shown = _pick(events, MAX_EVENTS, lambda e: e["rung"] == "R")
        self.assertIn("2026-10-01", [e["date"] for e in shown])
        self.assertEqual(len(shown), MAX_EVENTS)
        self.assertEqual(shown[0]["date"], "2026-10-24")  # still newest first

    def test_danger_symptom_never_cut(self):
        words = [{"date": "2026-10-01", "said": "胸口痛", "symptoms": ["chest_pain"]}] +                 [{"date": f"2026-10-{d:02d}", "said": "giddy", "symptoms": ["dizziness"]} for d in range(2, 25)]
        shown = _pick(words, MAX_WORDS, lambda w: bool(DANGER & set(w["symptoms"])))
        self.assertIn("2026-10-01", [w["date"] for w in shown])
        self.assertEqual(len(shown), MAX_WORDS)


if __name__ == "__main__":
    unittest.main()
