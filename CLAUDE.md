# CareLoop SG: notes for AI agents

Read this before changing anything. Then read [docs/build-log.md](docs/build-log.md) for what has been built, why, and what is still open.

## What this is

CareLoop SG supports Singapore seniors with hypertension between doctor visits. It stays quiet until something is actually wrong for *this* senior, then hands over to their family, or to their Active Ageing Centre (AAC) if they have no family, with the evidence.

- **Event:** Tencent Cloud Hackathon SG 2026, Healthcare track, NTU LKCMedicine Challenge 2.
- **Deadlines:** submission Fri 16 Oct 2026 23:59 SGT; team target 18:00; code freeze Thu 15 Oct 18:00.
- **Team (each owns a slice):**
  - Vibu: engine, contracts, API, data, evaluation.
  - Mingyu: senior app, language layer.
  - Nathan: caregiver app, design, reports, pitch.
- **Project brief:** a shared Claude Doc, "CareLoop SG — project brief". The main tab is the product; the "Build split" tab has each person's brief. Read it through a browser: the Docs connector cannot see it, because it was shared from another org.

## Rules that must not break

1. **Rules pick the rung. The model only understands and writes words.** The engine reaches a model only through `backend/language`: `understand(text, lang) -> Facts` and `write(rung, facts, lang) -> Message`. Never ask a model what rung to pick, whom to contact, or whether a number is dangerous.
2. **Red flags are never held back.** Rung R skips baseline, context, consent, cooldowns, the AAC cap and open handovers. Red-flag symptoms are detected by rules (`backend/language/extract.py`), never by the model alone. A model can add a symptom but never remove one.
3. **Numbers are extracted, never invented or rewritten.** A reading the language layer isn't sure of (confidence < 0.8) is confirmed by the senior. The trust check flags a bad reading; it never fixes it.
4. **Every outgoing message passes the guardrail** (`backend/language/guardrail.py`), or the fixed template for its rung goes out instead. Templates must pass the guardrail too (there's a test).
5. **CareLoop never decides on its own to contact anyone.** A handover waits for a person to pick one of its options; anything else ("just handle it") claims nothing.
6. **Thresholds live in one file**, `backend/engine/thresholds.json`. The red-flag floors are **PLACEHOLDER** until the medical student signs off. Don't put numbers anywhere else, and don't present them as clinical guidance.
7. **All people are synthetic.** No real patient data, ever. Clinical thresholds and the haze wording are labelled as what they are.
8. **The held-out evaluation set is frozen** (`backend/synth/heldout.json`, pinned by `HELDOUT.sha256`).
   - Never regenerate it, never tune on it, and never edit `docs/evaluation.md` by hand.
   - If you change the engine after a blind run, any re-run is **not blind**. Say so (see `docs/evaluation-notes.md`).
9. **Tests run offline**, with no keys and no network. data.gov.sg data comes from fixtures in `backend/env/fixtures/`; the model comes from `FakeGateway` or an empty `Chain([])`.
10. **Haze advice is MOH's, from a fixed table** (`backend/engine/config.py`). During haze a model draft may not mention masks or send the senior outdoors.

## Layout

```
contracts/          JSON Schema + example per object, endpoint table (frozen; changes need all three)
backend/
  language/         understand(), write(), guardrail, templates, model chain, speech-to-text   (Mingyu)
  engine/           trust, baseline, history, rules, ladder (run_day, claim), thresholds.json  (Vibu)
  env/              data.gov.sg PSI / rainfall / AAC + CC places, offline fixtures, suggest()  (Vibu)
  synth/            persona generator, tuning set, frozen held-out set, evaluate.py            (Vibu)
  api/              FastAPI app, store (SQLite or Postgres), demo seed + clock                 (Vibu)
  reports/          GP brief PDF (needs reportlab), insights, activities nearby, timetable import (Nathan)
  healthsync/       Apple Health and Health Connect records -> readings; phone simulator (Nathan)
web/                React + Vite, one build, two front doors
  senior/           /senior: big buttons, hold-to-talk, check-in, red flag, pairing           (Mingyu)
  care/             /care chooser, /care/family app, /care/aac centre console; ?demo clock   (Nathan)
  shared/           tokens.css (Nathan), i18n.ts (Mingyu), api.ts + contract.ts (Nathan)
docs/               architecture.md (+ diagrams), evaluation.md (blind, generated), evaluation-notes.md, build-log.md, tencent-tools.md
```

Each `backend/*/README.md` documents its own module.

## Run and test

```
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt     # bin/ on macOS/Linux
CARELOOP_SEED=demo .venv/Scripts/python -m uvicorn backend.api.app:app --port 8787
cd web && npm install && npm run dev:live         # uses web/.env.live (API on :8787); /senior?senior=tan, /care

for s in language engine api synth reports healthsync; do .venv/Scripts/python -m unittest discover -s backend/$s/tests -t .; done
cd web && npm run build                                                           # typecheck + build
python -m backend.synth.evaluate              # tuning set (ok to look at and tune on)
python -m backend.api.write_examples          # regenerate contracts/examples after changing shapes
```

- Without `VITE_API_URL`, both web apps run on in-browser mocks.
- Demo: `POST /demo/reset`, then `POST /demo/advance {"days": 11}` plays the video's fortnight for Mr Tan. Say "I'm fine lah, BP 186/112" into `/senior?senior=tan` for the red flag.

## Conventions

- **Backend:** Python 3.10+, standard library only, except `backend/api` (FastAPI). Tests use `unittest`. Every `tests/__init__.py` drops model and ASR keys so nothing can reach the network.
- **Contract shapes:** they live in `contracts/schemas`. If you change a shape, update the schema, regenerate the examples, and get the team's OK. The API tests validate every stored object against the schemas.
- **Web text:**
  - No hard-coded UI text in the senior app; strings go in `web/shared/i18n.ts`, in English and Chinese. Singlish speakers see English UI.
  - Senior-app styles use `web/shared/tokens.css` (from Tencent Design Miora) and must keep 48px+ tap targets, 18px+ text and AAA contrast.
- **Language codes:** `en`, `en-SG` (Singlish), `zh` (Mandarin). Rungs are the strings `"0"` to `"4"` and `"R"`.
- **Writing:** plain, short sentences, in comments, docs and UI alike. Say what is synthetic or a placeholder.
- **Tencent tools gate:** the hackathon requires proof that the project was built with CodeBuddy or WorkBuddy. Log every use in `docs/tencent-tools.md` with a screenshot. Claude Code sessions do not count as Tencent tool use.

## Pitfalls already hit

- **Windows:** Python's `write_text` writes CRLF and Git normalises to LF. That's why the held-out hash is a hash of the parsed JSON, not the bytes.
- **Escapes in heredocs:** when patching files through Python-in-bash heredocs, `\b` inside a non-raw string becomes a backspace character. Grep for `\x08` after such edits, or use the Edit tool.
- **Stacked PRs:** deleting a merged PR's branch closed the PR stacked on it (#2) instead of retargeting it. Reopen as a new PR against `main` (that is how #3 happened).
