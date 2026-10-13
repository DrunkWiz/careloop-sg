# backend/env

Haze (NEA 24-hour PSI by region), rain (NEA rainfall, nearest station), AAC and CC locations, all from data.gov.sg, with **offline fixtures**. Tests never hit the network.

Owner: Vibu.

- `fixtures/psi_2026-10-13.json`, `rainfall_2026-10-13.json`: real API responses from 13 Oct 2026, 17:00.
- `fixtures/places.json`:
  - MOH Eldercare Services (`d_f0fd1b3643ed8bd34bd403dedd7c1533`) and PA Community Clubs (`d_9de02d3fb33d96da1855f4fbef549a0f`), fetched 13 Oct 2026 and trimmed.
  - `kind: aac` is a name match (SAC / Silver ACE / Active Ageing). Homes and cluster offices are `eldercare_other` and are never suggested.
- `fetch_envday(day, region, live=True)` calls data.gov.sg (it pages the 5-minute rainfall). Default is the fixture.
- `suggest()`: the senior's own AAC programmes that fit what they like, then the nearest CC. Indoor only in rain or PSI > 100. "Not for me" is remembered. AAC timetables have no open feed: staff enter them (`PUT /aac/{id}/programmes`), and the demo seeds samples marked `sample: true`.
- Postal sector → PSI region is approximate (`data.py`).
