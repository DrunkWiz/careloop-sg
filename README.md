# CareLoop SG

CareLoop SG supports Singapore seniors with hypertension between doctor visits.
It stays quiet until something is wrong for *this* senior, then hands over to their family,
or to their Active Ageing Centre (AAC) if they have no family, with the evidence.

**Rules pick the rung. The model only understands and writes words.**

Tencent Cloud Hackathon SG 2026, Healthcare track, NTU LKCMedicine Challenge 2.

## The interfaces

One web build, three apps, one backend. A check-in on the senior app shows up in the family app and the centre console.

| Interface | Address | Who uses it |
|---|---|---|
| Home page | `/` | Everyone: three doors, for seniors, family and centres |
| **Senior app** | `/senior?senior=tan` | The senior: big buttons, hold-to-talk or type, English, Singlish or Mandarin |
| Role chooser | `/care` | Family or centre staff pick who they are |
| **Family app** | `/care/family?contact=tan-weiling` | Family: Today, Health, Plan, Activities, You |
| **CareLoop for Centres** | `/care/aac?worker=aac-siti` | AAC staff: Caseload, Report, Programmes |

The family app and the centre console also print a one-page **GP brief** (PDF) for the doctor.

Screenshots are from the synthetic demo after its fortnight (`POST /demo/advance {"days": 11}`). Mr Tan and Mr Ng are not real people.

**Steps** can come from a watch: `POST /reading` with `source: "watch"` takes the day's step total, heart rate and sleep, as Apple Health or Health Connect give them (a Fitbit syncs to both). A phone app to read them and send them in isn't built yet; in the demo, steps are synthetic. Blood pressure comes from the home cuff, said or typed into the check-in.

### Home page

<img src="docs/screenshots/home.png" alt="CareLoop home page with three doors" width="800">

### Senior app

A short daily check-in. Mr Tan can talk or type; CareLoop pulls out the reading and checks anything it isn't sure of.

<img src="docs/screenshots/senior.png" alt="Senior app check-in for Mr Tan" width="300">

### Family app

| Today | Health | A handover |
|---|---|---|
| <img src="docs/screenshots/family-today.png" alt="Family app Today tab" width="260"> | <img src="docs/screenshots/family-health.png" alt="Family app Health tab" width="260"> | <img src="docs/screenshots/family-handover.png" alt="Handover with evidence" width="260"> |
| Status, today's check-in, what CareLoop noticed, and every day's decision, quiet days included | 14 or 30 days of blood pressure against their usual, the medicine calendar and steps | Why CareLoop handed over, what it already tried, and the options. Nothing happens until someone picks one |

| Plan |
|---|
| <img src="docs/screenshots/family-plan.png" alt="Family app Plan tab" width="260"> |
| Shared by the whole family: appointments, questions for the doctor (printed on the GP brief), to-dos with owners, medicines and the emergency card |

### CareLoop for Centres

The caseload, sorted by who needs a look. At most one non-urgent alert per senior a week.

<img src="docs/screenshots/centre-caseload.png" alt="Centre caseload" width="800">

One senior: the day-by-day log, patterns in their own data, a befriending record ready to paste, and the care plan.

<img src="docs/screenshots/centre-senior.png" alt="Centre view of one senior" width="800">

Programmes: the centre types in its timetable once; CareLoop shows which seniors each programme suits and suggests them.

<img src="docs/screenshots/centre-programmes.png" alt="Centre weekly programmes" width="800">

## Layout

```
contracts/     schemas + example JSON for every object      (Vibu)
backend/
  engine/      trust check, baseline, context, rules, ladder, decision log   (Vibu)
  env/         data.gov.sg PSI + rainfall, with offline fixtures            (Vibu)
  synth/       persona generator, tuning set, frozen held-out set          (Vibu)
  language/    transcription, extraction, writer, guardrail                 (Mingyu)
  reports/     GP brief PDF, insights (patterns), activities nearby         (Nathan)
  api/         HTTP endpoints                                               (Vibu)
web/           React + Vite, one build: / home, /senior, /care
  shared/      design tokens, API client, i18n strings   (Nathan tokens, Mingyu i18n)
  senior/      the /senior app                           (Mingyu)
  care/        /care chooser, family app, centre console (Nathan)
docs/          evaluation, build log, user research, Tencent tools log, screenshots
```

## Run it

```
# API (Python 3.10+), seeded with the synthetic demo
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
CARELOOP_SEED=demo .venv/Scripts/python -m uvicorn backend.api.app:app --port 8787

# Web app against the API (web/.env.live points at :8787)
cd web && npm install && npm run dev:live
```

Without the API (`npm run dev`), the apps run on in-browser mocks in the same shapes.

**Home page:** `/`.

**Senior app:** `/senior?senior=tan` (the demo senior). Say "I'm fine lah, BP 186/112" for the red flag.

**Caregiver app:**
- `/care`: pick who you are. Family and centre staff get separate apps.
- `/care/family?contact=tan-weiling`: the family app (Today, Health, Plan, Activities, You). Use `?contact=tan-kelvin` in a second tab to act as Kelvin: claims show for both.
- `/care/aac?worker=aac-siti`: CareLoop for Centres, the AAC staff console. `/care/aac/programmes` is the timetable and who each programme suits.
- `?demo`: a bar to move the demo clock (+1 day, +11 days for the video's fortnight, reset). API only.
- Mocks only: `?scenario=quiet`, `?scenario=redflag` (both views).

## Tests and evaluation

Offline, with no keys and no network.

```
for s in language engine api synth reports; do .venv/Scripts/python -m unittest discover -s backend/$s/tests -t .; done
python -m backend.synth.evaluate --heldout     # docs/evaluation.md; read docs/evaluation-notes.md too
```

## Real vs synthetic

All senior data in this repo is synthetic. Clinical thresholds are placeholders until a clinician signs off.
