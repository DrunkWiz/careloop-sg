"""A centre's own calendar or spreadsheet becomes weekly programmes, with tags guessed from the titles."""
import unittest
from datetime import date
from pathlib import Path

from backend.reports.timetable import from_csv, parse, parse_days, parse_time

FIX = Path(__file__).resolve().parent.parent / "fixtures"
TODAY = date(2026, 10, 13)


def find(progs, title):
    return next(p for p in progs if p["title"] == title)


class IcsTest(unittest.TestCase):
    def setUp(self):
        self.progs, self.warnings = parse((FIX / "centre_calendar.ics").read_text(encoding="utf-8"), today=TODAY)

    def test_weekly_events_become_programmes(self):
        self.assertEqual(find(self.progs, "Qigong and stretching")["weekdays"], ["mon", "wed", "fri"])
        self.assertEqual(find(self.progs, "Qigong and stretching")["time"], "8:30am")
        self.assertIn("exercise", find(self.progs, "Qigong and stretching")["tags"])

    def test_same_event_on_two_days_is_merged(self):
        mj = [p for p in self.progs if p["title"] == "Mahjong afternoon"]
        self.assertEqual(len(mj), 1)
        self.assertEqual(mj[0]["weekdays"], ["tue", "thu"])

    def test_utc_times_are_shown_in_singapore_time(self):
        self.assertEqual(find(self.progs, "Karaoke sing-along")["time"], "10am")

    def test_guesses(self):
        walk = find(self.progs, "Brisk walk at the park connector")
        self.assertFalse(walk["indoor"])
        self.assertIn("walking", walk["tags"])
        phone = find(self.progs, "Smartphone class: WhatsApp video calls")
        self.assertFalse(phone["free"])  # "$5 per term" in the description
        self.assertTrue(find(self.progs, "Qigong and stretching")["indoor"])

    def test_one_offs_and_ended_runs_are_skipped_with_a_reason(self):
        titles = {p["title"] for p in self.progs}
        self.assertNotIn("Outing to Gardens by the Bay", titles)
        self.assertNotIn("Ukulele (June-July run)", titles)
        self.assertTrue(any("once" in w for w in self.warnings))
        self.assertTrue(any("ended" in w for w in self.warnings))


class CsvTest(unittest.TestCase):
    def setUp(self):
        self.progs, self.warnings = from_csv((FIX / "centre_timetable.csv").read_text(encoding="utf-8"))

    def test_rows_become_programmes(self):
        ex = find(self.progs, "Morning exercise")
        self.assertEqual((ex["weekdays"], ex["time"], ex["title_zh"]), (["mon", "wed", "fri"], "8:30am", "早操"))
        self.assertEqual(find(self.progs, "Communal lunch")["time"], "12pm")
        self.assertEqual(find(self.progs, "Bingo")["weekdays"], ["mon", "tue", "wed", "thu", "fri"])
        self.assertEqual(find(self.progs, "Bingo")["time"], "3:30pm")

    def test_columns_win_over_guesses(self):
        garden = find(self.progs, "Gardening club")
        self.assertEqual((garden["indoor"], garden["free"]), (False, False))
        self.assertIn("gardening", garden["tags"])

    def test_a_row_without_a_time_is_reported(self):
        self.assertNotIn("Line dancing", {p["title"] for p in self.progs})
        self.assertEqual(len(self.warnings), 1)
        self.assertIn("Row 8", self.warnings[0])

    def test_missing_columns(self):
        progs, warnings = from_csv("Name,Where\nKaraoke,Hall\n")
        self.assertEqual(progs, [])
        self.assertIn("first row", warnings[0])


class PartsTest(unittest.TestCase):
    def test_days(self):
        self.assertEqual(parse_days("Daily"), ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        self.assertEqual(parse_days("Sat - Mon"), ["mon", "sat", "sun"])
        self.assertEqual(parse_days("Tues and Thurs"), ["tue", "thu"])

    def test_times(self):
        self.assertEqual([parse_time(t) for t in ("08:30", "2.30pm", "12am", "14:00", "nope")], ["8:30am", "2:30pm", "12am", "2pm", None])


if __name__ == "__main__":
    unittest.main()
