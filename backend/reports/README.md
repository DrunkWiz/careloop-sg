# backend/reports

Weekly digest, handover pack, GP brief PDF. Every line traces to the decision log.

Owner: Nathan

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
