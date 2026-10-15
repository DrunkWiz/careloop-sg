"""Rota tests: on-duty sibling, red-flag bypass, AAC ignore, swap overrides, cooldown dedup."""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from backend.api.store import Store
from backend.engine import run_day, claim
from backend.engine.ladder import on_duty, contacts_for
from backend.engine.tests.helpers import World, START, TODAY, NO_MODEL


def _two_family_contacts(w: World):
    """Add a second family caregiver (c2) linked to the same senior as c1."""
    w.store.put("caregiver", {"id": "cg-2", "name": "Kelvin", "language": "en", "role": "family", "worker_id": None})
    w.store.put("contact", {"id": "c2", "caregiver_id": "cg-2", "senior_id": w.sid, "role": "family", "primary": False,
                            "name": "Kelvin", "language": "en", "worker_id": None,
                            "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})
    w.store.put("caregiver", {"id": "cg-3", "name": "Mei", "language": "zh", "role": "family", "worker_id": None})
    w.store.put("contact", {"id": "c3", "caregiver_id": "cg-3", "senior_id": w.sid, "role": "family", "primary": False,
                            "name": "Mei", "language": "zh", "worker_id": None,
                            "consent": {"family_sees": "readings", "share_words": True, "share_activity": True}})


def _put_rota(store, sid, mode, start, order, swaps=None):
    store.put("rota", {"id": f"rota-{sid}", "senior_id": sid, "mode": mode, "start_date": start.isoformat(),
                       "order": order, "swaps": swaps or []})


class TestOnDutyLogic(unittest.TestCase):
    """Tests 1-6: the on_duty function itself."""

    def test_1_weekly_rota_ab_week0_a_week1_b_week2_a(self):
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "weekly", START, ["c1", "c2"])
        self.assertEqual(on_duty(w.store, w.senior, START)["id"], "c1")           # week 0
        self.assertEqual(on_duty(w.store, w.senior, START + timedelta(7))["id"], "c2")   # week 1
        self.assertEqual(on_duty(w.store, w.senior, START + timedelta(14))["id"], "c1")  # week 2

    def test_2_daily_rota_abc_cycles(self):
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2", "c3"])
        self.assertEqual(on_duty(w.store, w.senior, START)["id"], "c1")
        self.assertEqual(on_duty(w.store, w.senior, START + timedelta(1))["id"], "c2")
        self.assertEqual(on_duty(w.store, w.senior, START + timedelta(2))["id"], "c3")
        self.assertEqual(on_duty(w.store, w.senior, START + timedelta(3))["id"], "c1")  # wraps

    def test_3_swap_overrides_for_that_date_only(self):
        w = World()
        _two_family_contacts(w)
        swap_day = START + timedelta(3)
        _put_rota(w.store, w.sid, "weekly", START, ["c1", "c2"],
                  swaps=[{"date": swap_day.isoformat(), "contact_id": "c2"}])
        # The swap day: c2 (not c1, which the weekly rotation would pick)
        self.assertEqual(on_duty(w.store, w.senior, swap_day)["id"], "c2")
        # The next day: back to the weekly rotation (c1)
        self.assertEqual(on_duty(w.store, w.senior, swap_day + timedelta(1))["id"], "c1")

    def test_4_before_start_none_no_rota_none_empty_none(self):
        w = World()
        _two_family_contacts(w)
        before = START - timedelta(1)
        # Before start_date
        _put_rota(w.store, w.sid, "weekly", START, ["c1", "c2"])
        self.assertIsNone(on_duty(w.store, w.senior, before))
        # No rota at all
        w.store.delete("rota", f"rota-{w.sid}")
        self.assertIsNone(on_duty(w.store, w.senior, TODAY))
        # Empty order
        _put_rota(w.store, w.sid, "weekly", START, [])
        self.assertIsNone(on_duty(w.store, w.senior, TODAY))

    def test_5_deleted_or_unlinked_contact_skipped(self):
        w = World()
        _two_family_contacts(w)
        # c2 is in the order but will be deleted; c1 is valid
        _put_rota(w.store, w.sid, "weekly", START + timedelta(7), ["c2", "c1"])
        # Delete c2's contact — c1 is still valid, so it should be returned
        w.store.delete("contact", "c2")
        duty = on_duty(w.store, w.senior, START + timedelta(7))
        self.assertEqual(duty["id"], "c1")
        # If all are invalid → None
        w.store.delete("contact", "c1")
        self.assertIsNone(on_duty(w.store, w.senior, START + timedelta(7)))

    def test_6_sgt_day_boundary(self):
        """on_duty takes a date; the caller (run_day) computes the SGT date. We verify the
        date boundaries are correct: 23:59 of one day vs 00:01 of the next pick different people
        when they fall on different rota periods."""
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2"])
        day_a = START + timedelta(6)   # index 6 % 2 = 0 → c1
        day_b = START + timedelta(7)   # index 7 % 2 = 1 → c2
        self.assertEqual(on_duty(w.store, w.senior, day_a)["id"], "c1")
        self.assertEqual(on_duty(w.store, w.senior, day_b)["id"], "c2")


class TestRotaRunDay(unittest.TestCase):
    """Tests 7-12: run_day targeting with a rota."""

    def test_7_rung4_handover_on_b_day_goes_to_b_only(self):
        """A rung-4 handover on B's day: the family message goes to B, not the primary A."""
        w = World()
        _two_family_contacts(w)
        # TODAY = START + 40; weekly index (40 // 7) % 2 = 1 → c2 (Kelvin's week)
        _put_rota(w.store, w.sid, "weekly", START, ["c1", "c2"])
        # Trigger a rung-4 (double dose)
        w.day(TODAY, bp=(124, 78), text="Aiyo I took my morning pill twice")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "4")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        self.assertEqual(len(fam), 1)
        self.assertEqual(fam[0]["contact_id"], "c2")  # on-duty, not primary

    def test_8_rung3_day_only_on_duty_sibling(self):
        """Rung 3 (digest/alert) goes to the on-duty sibling only."""
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2"])
        # Day 41 (today): daily index 41 % 2 = 1 → c2
        # Trigger a rung-3: a drift that's noted but not handed over yet
        w.day(TODAY, bp=(140, 90), text="Ok lah, today fine.")
        d = w.run(TODAY)
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        # Rung 3 messages family — check it goes to c2 (on duty)
        for m in fam:
            self.assertEqual(m["contact_id"], "c2")

    def test_9_red_flag_on_b_day_messages_all(self):
        """RED FLAG on B's day → messages to A, B AND C; the rota has no effect."""
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2", "c3"])
        # Today's daily index: 40 % 3 = 1 → c2 (on duty)
        # Trigger a red flag: very high BP
        w.day(TODAY, bp=(190, 125), text="Ok lah")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "R")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        contacts_messaged = {m["contact_id"] for m in fam}
        self.assertEqual(contacts_messaged, {"c1", "c2", "c3"})

    def test_10_red_flag_no_rota_still_all(self):
        """Red flag with no rota → still all caregivers (regression)."""
        w = World()
        _two_family_contacts(w)
        w.day(TODAY, bp=(190, 125), text="Ok lah")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "R")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        contacts_messaged = {m["contact_id"] for m in fam}
        self.assertEqual(contacts_messaged, {"c1", "c2", "c3"})

    def test_11_no_rota_rung4_goes_to_primary(self):
        """No rota → rung 4 goes to primary (the existing behaviour)."""
        w = World()
        _two_family_contacts(w)
        w.day(TODAY, bp=(124, 78), text="Aiyo I took my morning pill twice")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "4")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        self.assertEqual(len(fam), 1)
        self.assertEqual(fam[0]["contact_id"], "c1")  # primary

    def test_12_no_rota_no_primary_rung4_goes_to_all(self):
        """No rota and no primary → rung 4 goes to all (existing fallback)."""
        w = World()
        _two_family_contacts(w)
        # Remove primary from c1
        c1 = w.store.get("contact", "c1")
        c1["primary"] = False
        w.store.put("contact", c1)
        w.day(TODAY, bp=(124, 78), text="Aiyo I took my morning pill twice")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "4")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        contacts_messaged = {m["contact_id"] for m in fam}
        self.assertEqual(contacts_messaged, {"c1", "c2", "c3"})


class TestRotaEdgeCases(unittest.TestCase):
    """Tests 13-16: AAC, handover claim, cooldown, red flag never delayed."""

    def test_13_aac_senior_rota_ignored(self):
        """AAC-path senior with a rota stored → rota ignored, AAC contact messaged."""
        w = World(path="aac")
        # Store a rota (should be ignored for AAC)
        _put_rota(w.store, w.sid, "daily", START, ["c1"])
        # Trigger a rung-4 handover
        w.day(TODAY, bp=(124, 78), text="Aiyo I took my morning pill twice")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "4")
        # on_duty should return None for AAC
        self.assertIsNone(on_duty(w.store, w.senior, TODAY))
        # AAC contact should be messaged
        fam = [m for m in w.messages(d) if m["to"] == "aac"]
        self.assertTrue(len(fam) >= 1)

    def test_14_b_on_duty_a_claims_handover(self):
        """B is on duty but A claims the handover → allowed."""
        w = World()
        _two_family_contacts(w)
        # TODAY = START + 40; weekly index (40 // 7) % 2 = 1 → c2 is on duty
        _put_rota(w.store, w.sid, "weekly", START, ["c1", "c2"])
        w.day(TODAY, bp=(124, 78), text="Aiyo I took my morning pill twice")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "4")
        # c2 is on duty; c1 (not on duty) claims it
        ho_id = d["handover_id"]
        ho = claim(w.store, ho_id, "c1", "call")
        self.assertEqual(ho["claimed_by"], "c1")
        self.assertEqual(ho["status"], "claimed")

    def test_15_no_double_message_when_run_twice(self):
        """Cooldown/dedup: no double message to the on-duty sibling when run_day runs twice a day."""
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2"])
        w.day(TODAY, bp=(124, 78), text="I took my medicine twice")
        d1 = w.run(TODAY)
        self.assertEqual(d1["rung"], "4")
        fam1 = [m for m in w.messages(d1) if m["to"] == "family"]
        self.assertEqual(len(fam1), 1)
        # Run again — should not send a duplicate
        d2 = w.run(TODAY)
        fam2 = [m for m in w.messages(d2) if m["to"] == "family"]
        self.assertEqual(len(fam2), 1)  # same message, not duplicated
        self.assertEqual(d2["message_ids"], d1["message_ids"])

    def test_16_red_flag_never_delayed_by_rota(self):
        """A red flag is never delayed or held back by the rota (CLAUDE.md rule 2)."""
        w = World()
        _two_family_contacts(w)
        _put_rota(w.store, w.sid, "daily", START, ["c1", "c2", "c3"])
        # A red flag should reach ALL caregivers immediately
        w.day(TODAY, bp=(200, 130), text="I feel ok lah")
        d = w.run(TODAY)
        self.assertEqual(d["rung"], "R")
        fam = [m for m in w.messages(d) if m["to"] == "family"]
        # All three caregivers must be messaged
        contacts_messaged = {m["contact_id"] for m in fam}
        self.assertEqual(contacts_messaged, {"c1", "c2", "c3"})


if __name__ == "__main__":
    unittest.main()
