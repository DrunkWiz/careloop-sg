# backend/api

HTTP endpoints from the shared contract (`contracts/README.md`). FastAPI. Owner: Vibu.

```
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # (bin/ on macOS/Linux)
CARELOOP_SEED=demo .venv/Scripts/python -m uvicorn backend.api.app:app --port 8787
```

Then point the web app at it: `VITE_API_URL=http://localhost:8787 npm run dev` in `web/`. Open `/senior?senior=tan` to act as the demo senior.

**Hosting**: the two apps run on two phones and must share state, so this runs as ONE always-on service against ONE database. It never uses per-instance SQLite on serverless.
- `DATABASE_URL=postgresql://...` uses Postgres. For the deploy, use managed Postgres (TencentDB or Neon); install `psycopg[binary]`. This path hasn't been run yet.
- Otherwise it uses the SQLite file at `CARELOOP_DB` (default `careloop.db`): fine for the demo laptop and for a single always-on VM.

**Demo**:
- `CARELOOP_SEED=demo` seeds five synthetic seniors with 40 calm days. Two are family path (Mr Tan in Singlish, Mdm Wong in Mandarin); three are on Siti's AAC caseload (`aac-siti`).
- `POST /demo/advance {"days": 11}` plays the video's fortnight for Mr Tan: an odd reading (rung 1), pills running low (2), a drift noted (3), then handed over to Wei Ling (4).
- The red flag is said live into the senior app.
- Today's haze line uses the real 13 Oct PSI.

`python -m backend.api.write_examples` regenerates `contracts/examples/`.
