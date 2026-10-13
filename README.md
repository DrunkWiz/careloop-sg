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

## Run the web app

```
cd web
npm install
npm run dev
```

Open `/senior` or `/care`.

Without `VITE_API_URL` set, the web app runs on local mock data. Caregiver demo URLs:

- `/care`: drift handover (default) · `/care?scenario=quiet` · `/care?scenario=redflag`
- `?contact=c-weijie` to act as a second family member (claims show across tabs)
- `/care/pair`: pairing code and sharing choices

Set `VITE_API_URL` (e.g. in `web/.env.local`) to use the real backend.

## Real vs synthetic

All senior data in this repo is synthetic. Clinical thresholds are placeholders until a clinician signs off.
