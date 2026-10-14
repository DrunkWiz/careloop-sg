"""Steps from a watch arrive as the day's total so far, several times a day. The day keeps the largest."""
import unittest
from datetime import timedelta

from backend.engine import trust_check
from backend.engine.history import build

from .helpers import TODAY, World


class StepsSyncTest(unittest.TestCase):
    def test_repeated_syncs_are_not_added_up(self):
        w = World()
        d = TODAY
        w.day(d, steps=None)
        for i, (hhmm, count) in enumerate([("10:00", 1200), ("14:00", 3100), ("21:30", 4800)]):
            r = {"id": f"watch{i}", "senior_id": w.sid, "time": f"{d}T{hhmm}:00+08:00", "kind": "steps",
                 "values": {"count": count}, "source": "watch", "confidence": 1}
            w.store.put("reading", {**r, "trust": trust_check(r)})
        self.assertEqual(build(w.store, w.senior, d, days=2)[d].steps, 4800)

    def test_one_reading_a_day_is_unchanged(self):
        w = World()
        self.assertEqual(build(w.store, w.senior, TODAY - timedelta(1), days=2)[TODAY - timedelta(1)].steps, 5000)


if __name__ == "__main__":
    unittest.main()
