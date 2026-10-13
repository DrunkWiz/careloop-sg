import hashlib
import json
import unittest
from pathlib import Path

from backend.synth.generator import generate

HERE = Path(__file__).resolve().parents[1]


class Frozen(unittest.TestCase):
    def test_heldout_set_is_unchanged(self):
        want = (HERE / "HELDOUT.sha256").read_text().split()[0]
        got = hashlib.sha256((HERE / "heldout.json").read_bytes()).hexdigest()
        self.assertEqual(got, want, "the held-out set changed after it was frozen")

    def test_heldout_seed_is_recorded(self):
        data = json.loads((HERE / "heldout.json").read_text(encoding="utf-8"))
        self.assertEqual(data["seed"], 16102026)


class Generator(unittest.TestCase):
    def test_deterministic(self):
        a = [p.to_json() for p in generate(7, 2, prefix="x")]
        b = [p.to_json() for p in generate(7, 2, prefix="x")]
        self.assertEqual(a, b)

    def test_synthetic_and_labelled(self):
        for p in generate(7, 3, prefix="x"):
            self.assertTrue(p.events)
            self.assertTrue(all(r["source"] == "synthetic" for r in p.readings))
            self.assertTrue(all(e.expect in ("R", "4", "none") for e in p.events))


if __name__ == "__main__":
    unittest.main()
