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

# Web app (without VITE_API_URL the senior app uses an in-browser mock)
cd web && npm install && VITE_API_URL=http://localhost:8787 npm run dev
```

Open `/senior?senior=tan` (demo senior) or `/care`.

## Tests and evaluation

Offline, with no keys and no network.

```
for s in language engine api synth; do .venv/Scripts/python -m unittest discover -s backend/$s/tests -t .; done
python -m backend.synth.evaluate --heldout     # docs/evaluation.md; read docs/evaluation-notes.md too
```

## Real vs synthetic

All senior data in this repo is synthetic. Clinical thresholds are placeholders until a clinician signs off.
