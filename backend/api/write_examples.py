"""Regenerate contracts/examples/*.json from a real demo run, so examples never drift from the code.

    python -m backend.api.write_examples
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from . import app as api
from . import demo
from .store import Store

OUT = Path(__file__).resolve().parents[2] / "contracts" / "examples"


def build() -> dict[str, dict]:
    s = Store(":memory:")
    api.use_store(s)
    demo.seed(s)
    c = TestClient(api.app)
    c.post("/demo/advance", json={"days": 12})  # the drift is handed over on day 11
    c.get("/senior/tan/today")
    c.post("/checkin", json={"senior_id": "tan", "text": "I'm fine lah, BP 186/112 this morning", "source": "voice"})
    today = demo.today(s).isoformat()
    red = s.get("decision", f"dec-tan-{today}")
    drift = next(d for d in s.list("decision", senior_id="tan") if d["rung"] == "4")
    return {
        "Senior": s.get("senior", "tan"),
        "Caregiver": s.get("caregiver", "cg-weiling"),
        "Contact": s.get("contact", "tan-weiling"),
        "Reading": next(r for r in s.list("reading", senior_id="tan") if r["kind"] == "bp"),
        "CheckIn": s.list("checkin", senior_id="tan", day_from=today)[-1],
        "EnvDay": s.get("envday", f"env-{demo.DEMO_TODAY}-central"),
        "Decision": red,
        "Message": next(s.get("message", m) for m in red["message_ids"] if s.get("message", m)["to"] == "family"),
        "Handover": s.get("handover", drift["handover_id"]),
        "Suggestion": s.list("suggestion", senior_id="tan")[0],
        "Facts": s.list("checkin", senior_id="tan", day_from=today)[-1]["facts"],
        "VentPost": s.list("ventpost")[0],
        "Rota": s.get("rota", "rota-tan"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc in build().items():
        (OUT / f"{name}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
