"""Write the tuning and held-out sets.

The held-out set and its seed are frozen in git BEFORE any tuning: heldout.json is committed
with its SHA-256 in HELDOUT.sha256, and a test fails if either changes. Re-running this
script must never touch the held-out set once it exists; pass --force only to recreate it
from scratch (and say so in the PR).

    python -m backend.synth.freeze
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .generator import generate

HERE = Path(__file__).parent
TUNING_SEED = 20261013
HELDOUT_SEED = 16102026
N = 8


def write(name: str, seed: int, prefix: str) -> Path:
    personas = [p.to_json() for p in generate(seed, N, prefix=prefix)]
    path = HERE / f"{name}.json"
    path.write_text(json.dumps({"seed": seed, "n": N, "personas": personas}, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    """Hash of the parsed data, so line endings (CRLF on Windows checkouts) don't matter."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main() -> None:
    write("tuning", TUNING_SEED, "t")
    held = HERE / "heldout.json"
    if held.exists() and "--force" not in sys.argv:
        print("held-out set already frozen; left untouched")
    else:
        write("heldout", HELDOUT_SEED, "h")
        (HERE / "HELDOUT.sha256").write_text(sha256(held) + "  heldout.json\n", encoding="utf-8")
        print("froze held-out set:", sha256(held))


if __name__ == "__main__":
    main()
