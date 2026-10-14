# CareLoop SG

CareLoop SG supports Singapore seniors with hypertension between doctor visits.
Two apps, one codebase: a senior app (big buttons + voice, English/Singlish/Mandarin)
and a caregiver app with a family view and an AAC (Active Ageing Centre) view.
It stays quiet until something is wrong for *this* senior, then hands over with evidence.

**Rules pick the rung. The model only understands and writes words.**

Tencent Cloud Hackathon SG 2026, Healthcare track, NTU LKCMedicine Challenge 2.

## Layout

```
contracts/     schemas + example JSON for every object      (Vibu)
backend/
  engine/      trust check, baseline, context, rules, ladder, decision log   (Vibu)
  env/         data.gov.sg PSI + rainfall, with offline fixtures            (Vibu)
  synth/       persona generator, tuning set, frozen held-out set          (Vibu)
  language/    transcription, extraction, writer, guardrail                 (Mingyu)
  reports/     weekly digest, handover pack, GP brief PDF                   (Nathan)
  api/         HTTP endpoints                                               (Vibu)
web/           React + Vite, one build
  shared/      design tokens, API client, i18n strings   (Nathan tokens, Mingyu i18n)
  senior/      the /senior app                           (Mingyu)
  care/        the /care app: family view + AAC view     (Nathan)
docs/          README, evaluation page, Tencent tools log
```

## Run it

```
# API (Python 3.10+), seeded with the synthetic demo
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
CARELOOP_SEED=demo .venv/Scripts/python -m uvicorn backend.api.app:app --port 8787

# Web app against the API (web/.env.live points at :8787)
cd web && npm install && npm run dev:live
```

Without the API (`npm run dev`), both apps run on in-browser mocks in the same shapes.

**Senior app:** `/senior?senior=tan` (the demo senior).

**Caregiver app:**
- `/care`: pick who you are. Family and centre staff get separate apps.
- `/care/family?contact=tan-weiling`: the family app (Today, Health, Activities, Settings). Use `?contact=tan-kelvin` in a second tab to act as Kelvin: claims show for both.
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
