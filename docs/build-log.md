# Build log

What has been built, the decisions behind it, and what is still open. Newest first. Add to it when you finish a piece of work; keep each entry short.

## 15 Oct 2026: installable as phone apps (PWA)

- Each front door installs as its own app: `web/public/senior.webmanifest`, `family.webmanifest` and `centre.webmanifest` (own name, start page and icon; green for senior and family, navy for centres). `web/shared/pwa.ts` adds the right manifest, icon and theme colour per door; the home page and `/care` chooser stay plain web pages.
- `web/public/sw.js` keeps the app shell (pages, built files, icons) so it opens offline. It never caches API answers. Registered in production builds only.
- The family app and centre console remember the last `?contact=` and `?worker=` (an installed app opens without them). The family You tab has an "Add to home screen" card (a button on Android and Chrome, the Safari steps on iPhone, and the link for the senior's phone).
- Tested on the built app at 375px in Chrome: each door's manifest and icons load, the service worker activates and controls the page, Kelvin was remembered without `?contact=`, and with the web server stopped the app still opened from its saved copy. Not tested: installing on a real iPhone or Android phone, which needs the app hosted on HTTPS.

## 14 Oct 2026: watch steps, demo plans, README screenshots

- **Steps fix (engine, Vibu's file, changed at Nathan's request):** `backend/engine/history.py` added up every steps reading in a day. A watch syncing through Apple Health or Health Connect sends the day's running total several times, so each sync counted the day again (tested live: 1,064 + 900 became 1,964). A day now keeps the largest total. The synthetic personas send one steps reading a day, so tuning and held-out results don't change; any re-run is still not blind. Test: `backend/engine/tests/test_steps.py`.
- **Wearables, as they stand:** `POST /reading` takes `source: "watch"` for steps, heart rate and sleep, and they pass the trust check. Heart rate and sleep are stored but nothing reads them yet. Nothing on a phone reads Fitbit data from Apple Health or Health Connect: a web app can't, only an installed app can. Fitbit doesn't measure blood pressure; that still comes from the home cuff.
- **Demo plans:** the seed now writes Mr Tan's care plan (a past and a next GP visit, questions for the doctor, to-dos, emergency card; clinic, doctor, phone and address made up) and the timetable for the AAC-path seniors' centre, so the Plan tab and the Programmes page aren't empty. Test: `backend/api/tests/test_demo_plans.py`.
- **README:** the five interfaces, with screenshots from the demo in `docs/screenshots/`.

## 14 Oct 2026: app design and interaction fixes

- Added a shared home page at `/`, with separate senior, family and centre entry points and clearly labelled synthetic demos.
- Reworked the family layout for desktop and mobile; Health now leads with BP and medicine, provides 14/30-day periods (the insights backend has a 14-day minimum), and expands supporting findings on request. Added loading/retry and empty-chart states, and keyboard access to BP readings.
- Reworked the senior page with a daily completion indicator, large controls, a direct typing option, responsive layout, translated UI labels and persistent language choice. API-authored content still follows the senior's stored profile language; a full runtime language switch for that content remains a separate backend task.
- Fixed manual BP entry ignoring the API's urgent reply, duplicate text-form submissions, overlapping check-ins, and the client clock overriding the advanced demo date. No clinical thresholds or contract shapes changed.
- Review fixes: the senior app's logo is no longer a link (a stray tap took seniors out of their app to the home page); removed the repeated "CareLoop SG · name" line under the family masthead; raised meaningful 9–11px labels (Health tiles, findings, "Switch family", timeline dates) to 12px. Decorative spaced labels stay small.
- Validation: production TypeScript/Vite build; all 125 existing offline tests (54 language, 25 engine, 34 API, 4 synth, 8 reports); browser checks of desktop/390px layouts, 14-day period, one request per typed/pills submission, urgent BP response, and language persistence. Used a separate in-memory backend for mutations. Physical-phone speech recognition was not tested.
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
| Caregiver app `/care`, `/care/aac` | Done, on the API (contract shapes) or on mocks. A few API gaps: see open item 1 |
| Reports (`backend/reports`) | GP brief PDF done (`gp_brief_pdf`, one page, tested). Digest words are fixed templates in `web/care/digest.ts`; no model |
| Deck, video, README for judges | Not started (Nathan) |
| Tencent tools log | **Empty.** A submission gate: see open item 2 |

## Open items, most important first

1. **Caregiver app: what the API doesn't give it yet** (Vibu). The app now uses the contract shapes as they are; these are the gaps it works around:
   - **Same-day red flag has no handover (engine bug).** When a rung-4 handover already exists that day, a red flag the same day reuses its `handover_id` (`ladder.py`, `if out.rung in ("4", "R") and not decision["handover_id"]`), so no `red_flag` handover is made. Messages and `status` are right, so nothing is held back, but there is nothing to claim. The demo hits this: advance 11 days, then say the red flag. The app falls back to showing the message with "I've seen this".
   - **Caseload drops claimed handovers.** It returns only open ones, so a claimed row loses its "handling it" state.
   - **Caseload has no centre.** The app reads the AAC id and name from a senior's `brief.json` to find the programmes.
   - **Decision log endpoint added by Nathan** (`GET /senior/{id}/log`, in `backend/api/app.py`, tests in `test_log.py`): needs Vibu's OK. For a family contact it applies consent: `nothing` shows only red-flag days, `digest` hides numbers and the engine's reasons (they quote readings), `share_words: false` hides check-in words.
   - **No sample programmes in the seed.** The AAC timetable starts empty on the API.
   - **GP brief gaps.** `brief.json` has adherence for all medicines together, not per medicine, and nothing holds the family's questions (the brief leaves lines to write on).
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
   - Installing the app on a real phone (needs HTTPS hosting).
   - Fitbit data from a real phone: no app reads Apple Health or Health Connect yet (see 14 Oct, watch steps).
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
- **14 Oct, Nathan, branch `nathan/care-v2` (later):** features from 10 simulated personas and a desk review (`docs/user-research.md`; synthetic personas, not real interviews). Today so far (check-in time, pills, BP; Singapore time for family abroad); Care plan tab (appointments, questions for the doctor that print on the GP brief, shared to-dos with owners, medicines and refill reports, emergency card) on `GET/PUT /senior/{id}/care-notes` (added, needs team OK; new store kind `carenotes`); You tab (private caregiver check-in, AIC/respite/grants/SOS); bigger-text setting; centre Report tab with CSV export of every befriending record. Fixed family-app suggestion reasons that were the senior's own wording (and language).
- **14 Oct, Nathan, branch `nathan/care-v2`:** two separate front doors. `/care` asks who you are; `/care/family` is a phone-first family app (tabs: Today, Health, Activities, Settings; warm theme); `/care/aac` is "CareLoop for Centres", a dense console (stat tiles, filters, search, caseload table with a 7-day strip and "CareLoop noticed" column, two-column senior page). Smart analysis: `backend/reports/insights.py` (BP trend per week, this week against last, weekday miss patterns, BP the day after a missed dose, BP on social days, steps against usual, check-in punctuality; each finding states its n and is only made above a minimum). Activities pulled in automatically: `backend/reports/activities.py` (own AAC timetable or samples, nearest AACs and CCs from data.gov.sg, today's suggestions worked out with `suggest()` but not stored, answers). Programmes page shows which seniors each programme suits. Endpoints `/insights` and `/activities` added (need team OK); tests in `backend/api/tests/test_insights.py`. Offline fixtures recorded from the demo in `web/care/fixtures/`.
- **13 Oct, Nathan, branch `nathan/care-v2`:** caregiver app made fuller after a critique against the judging criteria. A 14-day timeline of every decision (quiet days included) for family and AAC, with each day's plain reason, words, pills and context; plain-language summaries per rule id (`web/care/plain.ts`), engine wording kept underneath; next-step help after a claim (GP note draft to copy, share or WhatsApp; polyclinic checklist; call or visit talking points; tap to dial 995); a "How this was decided" panel (rule, template or model, guardrail); redesigned home; week strips on caseload rows; tab badge and optional browser alerts while open. Added `GET /senior/{id}/log`.
- **13 Oct, Nathan, branch `nathan/care-api`:** `/care` and `/care/aac` moved onto the contract shapes and the real API (claims, pair codes, programmes, GP brief link), mocks rewritten in the same shapes, live refresh every 15 s, `?demo` bar for the video. GP brief PDF in `backend/reports`. Found the same-day red-flag handover bug (open item 1).
- **13 Oct, Nathan** (direct to `main`): `/care` family view and `/care/aac` AAC view on mock data, shared handover and red-flag screens, befriending record, programme timetable.
- **13 Oct, PR #1:** the senior app and the language layer (Mingyu's slice).
- **13 Oct:** repo skeleton (Nathan).

## How the evaluation went

See `docs/evaluation-notes.md`. In short:
- Both persona sets were frozen before any tuning.
- The engine was tuned on the tuning set only.
- One blind held-out run: 5 of 5 red flags, 16 of 17 real problems, no false handovers.
- The fixed "BP > 140" rule spots drifts sooner. That loss leads the evaluation page.
