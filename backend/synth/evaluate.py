"""Run the engine over personas day by day and score it against what was planted.

Reported in this order (main brief, "Real, simulated, and how we'll know it works"):
  1. Where we lost against a fixed rule (alert whenever BP > 140)
  2. Red flags caught: must be every one
  3. Real problems handed over, and how many days after onset
  4. False handovers per persona-month: the noise the family would actually get

    python -m backend.synth.evaluate              # tuning set, prints a summary
    python -m backend.synth.evaluate --heldout    # the frozen held-out set; writes docs/evaluation.md
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from backend.api.store import Store
from backend.engine import claim, run_day, trust_check
from backend.language import understand
from backend.language.gateway import Chain

HERE = Path(__file__).parent
GRACE = 7  # a handover up to 7 days after an event's last day still counts for that event
NO_MODEL = Chain([])


def load(store: Store, p: dict, upto: date | None = None) -> None:
    """Put a persona into a store. Check-ins go through understand() (rules only, offline)."""
    store.put("senior", p["senior"])
    for c in p["contacts"]:
        store.put("contact", c)
    for r in p["readings"]:
        if upto is None or r["time"][:10] <= upto.isoformat():
            store.put("reading", {**r, "trust": trust_check(r)})
    for c in p["checkins"]:
        if upto is None or c["time"][:10] <= upto.isoformat():
            facts = understand(c["raw_text"], c["language"], gateway=NO_MODEL)
            store.put("checkin", {**c, "facts": facts.to_dict()})
    for e in p["env"]:
        if upto is None or e["date"] <= upto.isoformat():
            store.put("envday", {"id": f"env-{e['date']}-{e['region']}", "forecast": None, "festival": None, "source": "synthetic", **e})


FAMILY_RESPONDS_AFTER = 1  # simulated: the family or AAC picks a next step the day after a handover


def run_persona(p: dict) -> list[dict]:
    store = Store(":memory:")
    load(store, p)
    start = date.fromisoformat(p["start"])
    contact = p["contacts"][0]["id"]
    out = []
    for i in range(p["days"]):
        day = start + timedelta(i)
        for h in store.list("handover", senior_id=p["senior"]["id"]):
            if h["status"] == "open" and (day - date.fromisoformat(h["opened_at"][:10])).days >= FAMILY_RESPONDS_AFTER:
                claim(store, h["id"], contact, h["options"][0]["id"])
        out.append(run_day(store, p["senior"]["id"], day, gateway=NO_MODEL))
    return out


@dataclass
class Score:
    personas: int = 0
    persona_days: int = 0
    red_total: int = 0
    red_caught: int = 0
    red_missed: list[str] = field(default_factory=list)
    real_total: int = 0
    drift_total: int = 0
    real_caught: int = 0
    delays: list[int] = field(default_factory=list)
    real_missed: list[str] = field(default_factory=list)
    false_handovers: int = 0
    false_detail: list[str] = field(default_factory=list)
    benign_quiet: int = 0
    benign_total: int = 0
    rungs: dict[str, int] = field(default_factory=dict)
    # the fixed rule: alert on any day with a BP reading over 140
    fixed_alerts: int = 0
    fixed_false: int = 0
    fixed_red_caught: int = 0
    fixed_real_caught: int = 0
    fixed_delays: list[int] = field(default_factory=list)
    losses: list[str] = field(default_factory=list)


def score(personas: list[dict]) -> Score:
    sc = Score()
    for p in personas:
        decisions = run_persona(p)
        sid, name = p["senior"]["id"], p["senior"]["name"]
        sc.personas += 1
        sc.persona_days += p["days"]
        by_day = {d["date"]: d for d in decisions}
        for d in decisions:
            sc.rungs[d["rung"]] = sc.rungs.get(d["rung"], 0) + 1
        handovers = [date.fromisoformat(d["date"]) for d in decisions if d["rung"] == "4"]
        over140 = sorted({date.fromisoformat(r["time"][:10]) for r in p["readings"]
                          if r["kind"] == "bp" and r["values"]["systolic"] > 140})
        sc.fixed_alerts += len(over140)

        windows = []
        for e in p["events"]:
            s, end = date.fromisoformat(e["start"]), date.fromisoformat(e["end"])
            tag = f"{sid} {name}: {e['kind']} {e['start']}"
            if e["expect"] == "R":
                sc.red_total += 1
                ok = by_day.get(e["start"], {}).get("rung") == "R"
                sc.red_caught += ok
                if not ok:
                    sc.red_missed.append(tag)
                fixed = s in over140 and e["kind"] == "red_flag_bp"
                sc.fixed_red_caught += fixed
                if fixed and not ok:
                    sc.losses.append(f"{tag}: the fixed rule alerted that day; CareLoop did not reach R")
                windows.append((s, s + timedelta(GRACE)))
            elif e["expect"] == "4":
                sc.real_total += 1
                sc.drift_total += e["kind"] == "drift"
                hit = next((h for h in handovers if s <= h <= end + timedelta(GRACE)), None)
                # a red flag inside the window also gets it in front of the family
                hit = hit or next((date.fromisoformat(d["date"]) for d in decisions
                                   if d["rung"] == "R" and s <= date.fromisoformat(d["date"]) <= end + timedelta(GRACE)), None)
                # The fixed rule only sees BP, so it only gets credit on BP events.
                fixed_hit = next((x for x in over140 if s <= x <= end + timedelta(GRACE)), None) if e["kind"] == "drift" else None
                if hit:
                    sc.real_caught += 1
                    sc.delays.append((hit - s).days)
                else:
                    sc.real_missed.append(tag)
                if fixed_hit:
                    sc.fixed_real_caught += 1
                    sc.fixed_delays.append((fixed_hit - s).days)
                if fixed_hit and (not hit or fixed_hit < hit):
                    lag = f"{(hit - fixed_hit).days} days later" if hit else "and CareLoop never handed over"
                    sc.losses.append(f"{tag}: the fixed rule alerted on {fixed_hit}, CareLoop {lag}")
                windows.append((s, end + timedelta(GRACE)))
            else:
                sc.benign_total += 1
                quiet = not any(s <= h <= end + timedelta(3) for h in handovers)
                sc.benign_quiet += quiet
        for h in handovers:
            if not any(a <= h <= b for a, b in windows):
                sc.false_handovers += 1
                sc.false_detail.append(f"{sid} {name}: rung 4 on {h}: {by_day[h.isoformat()]['rule_id']}")
        sc.fixed_false += sum(1 for x in over140 if not any(a <= x <= b for a, b in windows))
    return sc


def report(sc: Score, label: str, seed: int) -> str:
    months = sc.persona_days / 30
    avg = lambda xs: f"{sum(xs) / len(xs):.1f}" if xs else "n/a"
    lines = [
        f"# Evaluation: {label}",
        "",
        f"{sc.personas} synthetic personas, {sc.persona_days} persona-days ({months:.1f} persona-months), seed {seed}. "
        "Rules only, no model, fully offline. Clinical thresholds are placeholders until a clinician signs off. "
        "Generated by `python -m backend.synth.evaluate --heldout`; do not edit by hand.",
        "",
        "## 1. Where we lost against a fixed rule",
        "",
        "The fixed rule alerts the family on every day with a reading over 140.",
        "",
    ]
    lines += [f"- {x}" for x in sc.losses] or ["- No event where the fixed rule beat CareLoop."]
    lines += [
        "",
        "| | CareLoop | Fixed rule (BP > 140) |",
        "| --- | --- | --- |",
        f"| Red flags caught | {sc.red_caught} of {sc.red_total} | {sc.fixed_red_caught} of {sc.red_total} |",
        f"| Real problems flagged | {sc.real_caught} of {sc.real_total} | {sc.fixed_real_caught} of {sc.drift_total} BP drifts (sees nothing else) |",
        f"| Days from onset, average | {avg(sc.delays)} | {avg(sc.fixed_delays)} (drifts only) |",
        f"| Alerts outside real events, per persona-month | {sc.false_handovers / months:.2f} | {sc.fixed_false / months:.2f} |",
        "",
        "## 2. Red flags caught (must be every one)",
        "",
        f"**{sc.red_caught} of {sc.red_total}.** " + ("PASS." if sc.red_caught == sc.red_total else "FAIL: a single miss is a failing result."),
    ]
    lines += [f"- Missed: {x}" for x in sc.red_missed]
    lines += [
        "",
        "## 3. Real problems handed over",
        "",
        f"{sc.real_caught} of {sc.real_total} (drift, missed medicine, unwell for days, isolation), on average "
        f"{avg(sc.delays)} days after onset.",
    ]
    lines += [f"- Missed: {x}" for x in sc.real_missed]
    lines += [
        "",
        "## 4. False handovers per persona-month",
        "",
        f"{sc.false_handovers} handovers outside any real event: **{sc.false_handovers / months:.2f} per persona-month**. "
        f"Look-alike events left quiet (haze, rain, mahjong, phone at home, CNY): {sc.benign_quiet} of {sc.benign_total}.",
    ]
    lines += [f"- {x}" for x in sc.false_detail]
    lines += ["", "## Rungs over all persona-days", "", "| Rung | Days |", "| --- | --- |"]
    lines += [f"| {r} | {sc.rungs.get(r, 0)} |" for r in ["0", "1", "2", "3", "4", "R"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout", action="store_true", help="score the frozen held-out set and write docs/evaluation.md")
    args = ap.parse_args()
    name = "heldout" if args.heldout else "tuning"
    data = json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))
    sc = score(data["personas"])
    text = report(sc, f"{name} set", data["seed"])
    if args.heldout:
        out = HERE.parent.parent / "docs" / "evaluation.md"
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    print(text)


if __name__ == "__main__":
    main()
