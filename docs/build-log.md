# Build log

What has been built, the decisions behind it, and what is still open. Newest first. Add to it when you finish a piece of work; keep each entry short.

## Status, Tue 13 Oct 2026 evening

| Piece | State |
| --- | --- |
| `contracts/` | Done. 10 schemas and examples. **Not yet confirmed by Vibu**, who was due to freeze it at 23:00 |
| Language layer | Done. Rules plus model chain (Hunyuan, then a fallback, then rules and templates), guardrail, templates. No model key has been tried yet |
| Engine | Done. 20 safety scenarios pass. Thresholds are placeholders |
| Env data | Done on fixtures. The live data.gov.sg fetch exists but no daily job calls it |
| API | Done on SQLite. The Postgres path hasn't been run |
| Evaluation | Done. Blind held-out result in `docs/evaluation.md` |
| Senior app `/senior` | Done, against the API or mocks. Hold-to-talk untested on a real phone |
| Caregiver app `/care`, `/care/aac` | Built by Nathan **on mocks**; **not yet wired to the API** (see open item 1) |
| Reports (`backend/reports`) | Not started: GP brief PDF, digest text. Data is ready at `GET /senior/{id}/brief.json` and in `GET /care/family/{contact}` |
| Deck, video, README for judges | Not started (Nathan) |
| Tencent tools log | **Empty.** A submission gate: see open item 2 |

## Open items, most important first

1. **The caregiver app doesn't match the API yet.** `web/shared/contract.ts` and `web/shared/api.ts` were written before `contracts/` existed. Known differences:
   - **Claim body:** `POST /handover/{id}/claim` takes `{contact_id, choice}`; the app sends `option_id`.
   - **Rungs:** strings `"0"` to `"4"` and `"R"` in the API; numbers in the app.
   - **Senior:** `home_postal` (not `home_postal_code`). Medicines are `{name, dose_text, schedule, started, for_bp}`. Language includes `en-SG`.
   - **Handover:** `kind` is one of `bp_drift`, `missed_medicine`, `unwell`, `activity`, `no_contact`, `double_dose`, `red_flag`. The chosen option is `choice`.
   - **Family view and caseload:** `GET /care/family/{contact}` and `GET /care/aac/{worker_id}/caseload` return different shapes from `FamilyView` / `AacCaseload`. The caseload is keyed by the AAC worker (`worker_id`), not a contact id.
   - **Programmes:** saving them has an endpoint now: `PUT /aac/{aac_id}/programmes`.

   Decide together whether the app adopts `contracts/` or the API adds adapters. The contract says changes need all three to agree.
2. **Tencent tools gate.** Per the handbook, the project is not scored without proof it was built with CodeBuddy or WorkBuddy. Nothing is logged in `docs/tencent-tools.md` yet. Plan:
   - CodeBuddy for building and tests.
   - WorkBuddy for the weekly digest and GP brief if it fits.
   - Miora for design.
3. **Clinical sign-off** by the medical student (by Thu):
   - The red-flag floors in `thresholds.json`.
   - The red-flag message wording in `backend/language/templates.py`.
   - The double-dose rule.
4. **Decisions Vibu still has to confirm:**
   - **Hosting:** one always-on service plus managed Postgres for the deploy; SQLite on the demo laptop.
   - **New endpoints:** `/pair`, `/care/pair-code`, the suggestion response, `/aac/{id}/programmes`, `brief.json`.
   - **Invented rules:**
     - A double dose is rung 4.
     - "No reply for 3 days" is rung 3 for family-path seniors but rung 4 for AAC-path seniors.
     - PSI above 300 is rung 3.
5. **Untested paths:**
   - A real Hunyuan key (`HUNYUAN_API_KEY`).
   - Tencent Cloud ASR (`transcribe()`).
   - Postgres.
   - Hold-to-talk over HTTPS on a phone (the Web Speech API needs HTTPS or localhost).
6. **Still to collect:** the real family story for the video opening (with consent), and optionally a quote from an AAC worker.

## Decisions

| Decision | Why |
| --- | --- |
| Backend in Python, standard library except the API (FastAPI) | Few dependencies for a 3-day build; the language layer and engine import anywhere |
| Speech-to-text in the browser (Web Speech API, `en-SG` and `zh-CN`) | Free and needs no key; server-side Tencent ASR is a fallback for audio uploads |
| Model chain: Hunyuan (OpenAI-compatible) → optional fallback → rules and templates | Hunyuan helps the Tencent score; the last rung keeps the demo alive with no network |
| Rules always run first in `understand()`; the model may only add | A model outage or a misread "I'm fine lah" can't hide a red flag |
| Mask mentions are rejected during haze | MOH: N95s only above PSI 200, and only for several hours outdoors; a blanket "wear a mask" contradicts it for heart patients |
| BP baseline = median of the 30 days before the recent week; steps baseline excludes the last 14 days | A drift in progress, or two weeks of isolation, can't become the new normal |
| 14-day cooldown per handover kind; the table looks past a cooling-down kind for other problems | Stops daily repeat handovers without letting an old problem hide a new one (found by the blind run) |
| The AAC weekly cap counts handovers only; digest notes are a quiet caseload row | A trivial note used up the week's alert and blocked a real handover (found in tuning) |
| A swapped BP pair is checked against red-flag floors both ways | 112/186 is far more likely 186/112 than a safe reading |
| `?senior=tan` opens the senior app as a demo senior | For the video; pairing is still the real flow |

## History

- **13 Oct, PR #3** (reopens #2): contracts, engine, env, API, synth, evaluation; senior app wired to the API. The work was Vibu's slice, built in a Claude Code session at Mingyu's request so nobody was blocked; Vibu should review it as inherited code.
  - **Bugs found by tests and evaluation, fixed:**
    - Mandarin chest pain with words in between ("胸口有点痛") wasn't a red flag.
    - "Wear a mask and go for your walk" passed the guardrail.
    - Handovers were stamped with wall-clock time instead of the decision day.
    - The AAC cap blocked real handovers.
    - An old handover hid a new problem.
    - The CRLF hash pin broke on other machines.
- **13 Oct, Nathan** (direct to `main`): `/care` family view and `/care/aac` AAC view on mock data, shared handover and red-flag screens, befriending record, programme timetable.
- **13 Oct, PR #1:** the senior app and the language layer (Mingyu's slice).
- **13 Oct:** repo skeleton (Nathan).

## How the evaluation went

See `docs/evaluation-notes.md`. In short:
- Both persona sets were frozen before any tuning.
- The engine was tuned on the tuning set only.
- One blind held-out run: 5 of 5 red flags, 16 of 17 real problems, no false handovers.
- The fixed "BP > 140" rule spots drifts sooner. That loss leads the evaluation page.
