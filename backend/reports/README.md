# backend/reports

Weekly digest, handover pack, GP brief PDF. Every line traces to the decision log.

Owner: Nathan

## Timetable import

`timetable.parse(text, today=...)` reads a centre's own timetable: a calendar (.ics, as Google Calendar or
Outlook export it, or a calendar link) or a spreadsheet (.csv with columns for the programme, days and
time). Weekly events become programmes; one-off events and runs that have ended are skipped with a reason.
Tags (the words seniors' likes use), indoor or outdoor, and free or not are guessed from each title by
keyword rules, and shown before anything is saved. There's no open feed of AAC or CC programmes, so this
is the way in without retyping. `POST /aac/{id}/programmes/import` calls it; a saved calendar link is
pulled again once a day.

## GP brief

`gp_brief_pdf(data) -> bytes` turns the dict from `GET /senior/{id}/brief.json` into a one-page A4 PDF.
`GET /senior/{id}/brief.pdf` calls it. No model is involved: the page only lays out what the decision
log already says.

On the page:
- **Blood pressure, last 7 days**, against their own baseline
- **Medicines**, as days taken out of days reported
- **Daily chart** over the period, with rung 3+ events marked above it
- **What CareLoop flagged**: each event with its decision log id
- **In their own words**: what the senior said, in English, Singlish or Mandarin, with the symptoms picked out
- **Questions for this visit**, with blank lines to write on
- **Their Active Ageing Centre**, if any

It is always one page: long lists show the most recent entries and say how many are left out, and the
layout shrinks to fit. Mandarin uses the built-in STSong-Light CID font, so no font file is shipped.

```
pip install reportlab==4.2.5
python -m backend.reports.gp_brief brief.json brief.pdf
python -m unittest discover -s backend/reports/tests -t .
```

The API imports this lazily, so without reportlab only `brief.pdf` fails (501), not the whole API.

## Insights (`insights.py`)

Patterns in one senior's own data, for the Health tab and the centre console (`GET /senior/{id}/insights`).
Plain statistics over the engine's daily history, no model: BP trend (least-squares slope per week), this week
against last, weekday patterns in missed doses, BP the day after a missed dose, BP on social days against other
days, steps against their usual, check-in punctuality, haze days. Each finding carries `n`, the days or readings
it rests on, and is only made above a minimum (`MIN_*` at the top of the file). They are patterns, not causes
or diagnoses, and the app says so. It never picks a rung or contacts anyone: the rules do that.

## Activities (`activities.py`)

`GET /senior/{id}/activities`: the senior's own AAC and its weekly programmes (entered by staff, or the
samples), the nearest AACs and community clubs from data.gov.sg with distances, what CareLoop would suggest
today (worked out with `backend/env/places.suggest()`, not stored), and the last two weeks' suggestions with
the senior's answers. Read-only.
