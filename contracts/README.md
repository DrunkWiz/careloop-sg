# contracts

The shared contract: one JSON Schema and one example per object. The senior app (Mingyu), the caregiver app (Nathan) and the API (Vibu) all build against it.

Owner: Vibu. Frozen Tue 13 Oct 23:00. **After the freeze, a change needs all three to agree in the group chat.**

- `schemas/<Object>.schema.json`: JSON Schema 2020-12.
- `examples/<Object>.json`: real output of a demo run. Regenerate with `python -m backend.api.write_examples`. A test validates every example and every stored object against these schemas.

## Objects

| Object | What it is |
| --- | --- |
| Senior | The person. Language, postal region (for PSI), path (`family` or `aac`), medicines, likes, consent, and remembered "not for me"s |
| Contact | A family member or AAC staff (`worker_id` groups an AAC caseload). Any number can be primary; the first to claim a handover owns it |
| Reading | `bp`, `hr`, `steps`, `sleep` or `glucose`, with the trust check's verdict |
| CheckIn | What the senior said, plus `facts` from `understand()` |
| Facts | `understand()` output (backend/language) |
| EnvDay | 24-hour PSI and rainfall per region per day, plus festival |
| Decision | One per senior per day, rung 0 included, with rule id, reason and every number used |
| Message | Words from `write()`, with the guardrail verdict and which model (if any) wrote it |
| Handover | Rung 4 or R evidence pack, 2-3 options, and who claimed it |
| Suggestion | Up to 3 a day: the senior's own AAC first, then the nearest CC |

## Endpoints

| Endpoint | Used by |
| --- | --- |
| `POST /checkin` `{senior_id, text, language?, source}` → `{checkin_id, facts, message, rung}` | Senior app |
| `POST /reading` `{senior_id, kind, values, source, confidence}` → `{reading, rung, message}` | Senior app, watch import |
| `GET /senior/{id}/today` (buttons state, haze line, suggestions) | Senior app |
| `GET /senior/{id}/knows`, `DELETE /senior/{id}/knows/{fact}` | Senior app |
| `POST /senior/{id}/suggestions/{sid}/response` `{response: not_for_me \| going}` **(added)** | Senior app |
| `POST /pair` `{code, language, consent}` **(added)** | Senior app |
| `POST /care/pair-code` `{contact_name, role, senior_name, home_postal, aac_id?}` → `{code}` **(added)**; AAC path: the new senior joins `aac_id`, or the worker's usual centre if omitted | Both care views |
| `GET /care/family/{contact}` (digest numbers, handovers, status) | Family view |
| `GET /care/aac/{worker_id}/caseload` | AAC view |
| `GET/PUT /aac/{aac_id}/programmes` (weekly timetable, entered once) **(added)** | AAC view |
| `POST /handover/{id}/claim` `{contact_id, choice}`; 400 if `choice` isn't an option | Both care views |
| `GET /senior/{id}/brief.json` (everything the GP brief needs) **(added)** | Family view, reports |
| `GET /senior/{id}/brief.pdf` (one-page GP brief, `backend/reports`) | Family view |
| `GET /senior/{id}/log?days=14&contact={id}` (every day's decision, rung 0 included; consent applied for family) **(added)** | Family timeline, AAC befriending record |
| `GET /senior/{id}/insights?days=30&contact={id}` (patterns in their own data, `backend/reports/insights.py`; consent applied) **(added)** | Family Health tab, centre console |
| `GET /senior/{id}/activities?contact={id}` (own AAC programmes, nearest AACs and CCs, today's suggestions) **(added)** | Family Activities tab, centre console |
| `GET/PUT /senior/{id}/care-notes?contact={id}` (appointments, questions for the doctor, shared to-dos, emergency card; any linked contact; new store kind `carenotes`) **(added)** | Family Plan tab, centre console, GP brief |
| `POST /demo/advance` `{days}`, `POST /demo/reset` | Demo only |
| `GET /meta` (model chain, data sources, version) | Everyone |

**(added)** marks endpoints that weren't in the build-split table but the apps need. They need the team's OK.

## The one boundary that matters

The engine calls the model only through `understand(text, lang) -> Facts` and `write(rung, facts, lang) -> Message` (backend/language). The engine never asks the model what rung to pick.
