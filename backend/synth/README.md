# backend/synth

Synthetic personas with planted events. No real patient data. Owner: Vibu.

- `generator.py`: 90 days of BP, steps, check-in replies (English, Singlish, Mandarin) and weather. Planted events carry dates and the expected outcome (`R`, `4` or `none`).
- `tuning.json`: 8 personas, seed 20261013. Look at it, tune on it.
- `heldout.json`: 8 personas, seed 16102026. **Frozen before tuning** and pinned by `HELDOUT.sha256`; a test fails if it changes. `python -m backend.synth.freeze` never touches it without `--force`.
- `evaluate.py`: runs the engine day by day and reports, in this order: where we lost against a fixed rule (alert whenever BP > 140), red flags caught, real problems handed over and days after onset, and false handovers per persona-month.

```
python -m backend.synth.evaluate              # tuning set
python -m backend.synth.evaluate --heldout    # writes docs/evaluation.md
```

See `docs/evaluation-notes.md` for what happened around the blind run.
