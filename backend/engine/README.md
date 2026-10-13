# backend/engine

Trust check → personal baseline → context → rule table → ladder → decision log. Rules pick the rung; the model only understands and writes words (through `backend.language`).

Owner: Vibu. Standard library only.

| File | What |
| --- | --- |
| `thresholds.json` | Every number, in ONE file. Red-flag floors are **PLACEHOLDER** until the medical student signs off |
| `trust.py` | Flags impossible, swapped and wrong-unit readings. Never fixes a number. Red-flag floors are checked on both orders of a swapped pair |
| `history.py` | One summary per senior per day, from readings, check-ins and EnvDays |
| `baseline.py` | BP: median of the 30 days before the recent week. Steps: excludes the last 14 days |
| `rules.py` | The rule table, top to bottom, first match wins: R, open handover, 4, 3, trust ask, 2, 1, 0 |
| `ladder.py` | `run_day()`: consent, the AAC weekly cap, the same-problem cooldown, decision log, handover, messages. `claim()` |

`run_day(store, senior_id, day)` is safe to re-run; every check-in does. Within a day a red flag or handover stands.

Rungs: 0 nothing (logged with reason) · 1 ask · 2 suggest · 3 note in digest · 4 hand over · R red flag (skips baseline and context).

```
python -m unittest discover -s backend/engine/tests -t .     # includes the 20 safety scenarios
```
