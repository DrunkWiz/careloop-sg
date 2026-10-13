"""What there is to do near a senior, pulled in automatically, for the caregiver app. Owner: Nathan.

- Their own Active Ageing Centre and its weekly programmes: the timetable staff entered, or the sample
  programmes (marked sample) when none is entered yet.
- The nearest other AACs and community clubs, from data.gov.sg (MOH Eldercare Services, PA Community
  Clubs) via backend/env/places.py, with distance from home.
- What CareLoop suggested in the last two weeks and how the senior answered ("going", "not for me").
- Whether today calls for indoor options (rain or haze), from the same EnvDay the engine reads.

Read-only. Standard library only.
"""
from __future__ import annotations

from datetime import date, timedelta

from backend.engine.config import T
from backend.engine.history import build
from backend.env.data import _km
from backend.env.places import WEEKDAYS, _fits, home_point, place, places, sample_programmes, suggest


def activities(store, senior: dict, today: date, *, responses: bool = True) -> dict:
    """responses=False hides how the senior answered suggestions (share_activity is off)."""
    home = home_point(senior)
    likes = senior.get("likes", [])
    own = place(senior.get("aac_id") or "")
    own = own if own and own["kind"] == "aac" else None

    progs = []
    if own:
        stored = [p for p in store.list("programme") if p.get("place_id") == own["id"]]
        for p in stored or sample_programmes(own["id"]):
            like = _fits(likes, p.get("tags", []))
            progs.append({**p, "fits": like})
        progs.sort(key=lambda p: (p["fits"] is None, p["title"]))

    def near(kind: str, n: int, skip: set[str]) -> list[dict]:
        ranked = sorted((p for p in places() if p["kind"] == kind and p["id"] not in skip), key=lambda p: _km((p["lat"], p["lon"]), home))
        return [{"id": p["id"], "kind": p["kind"], "name": p["name"], "address": p.get("address"), "postal": p.get("postal"),
                 "km": round(_km((p["lat"], p["lon"]), home), 1), "lat": p["lat"], "lon": p["lon"]} for p in ranked[:n]]

    hidden = set(senior.get("hidden_suggestions", []))
    sugs = store.list("suggestion", senior_id=senior["id"], day_from=(today - timedelta(13)).isoformat(), day_to=today.isoformat())
    sugs = sorted(sugs, key=lambda s: (s["date"], s["id"]), reverse=True)

    d = build(store, senior, today, days=1)[today]
    act = T["activity"]
    rainy = d.rain_mm is not None and d.rain_mm >= act["rain_mm"]
    hazy = (d.psi or 0) > act["haze_psi_above"]
    weekday = WEEKDAYS[today.weekday()]
    # What CareLoop would suggest today, worked out the same way the senior app's card is, but not stored.
    stored = [p for p in store.list("programme") if p.get("place_id") == (own or {}).get("id")] or None
    today_sugs = suggest(senior, today, indoor_only=rainy or hazy, programmes=stored)
    by_id = {p["id"]: p for p in progs}

    def for_family(s: dict) -> str:
        """The engine words why_it_fits to the senior ("You said you like…", in their language). The family
        app needs it about them, in English: rebuilt here from the same facts."""
        if s["kind"] == "programme":
            like = (by_id.get(s["place_id"]) or {}).get("fits")
            return f"They like {like}" if like else "At their own centre"
        if s["kind"] == "cc":
            cc = place(s["place_id"])
            return f"Nearest community club, about {_km((cc['lat'], cc['lon']), home):.1f} km" if cc else "Nearest community club"
        return "Active Ageing Centre near them"

    def title_en(s: dict) -> str:
        if s["kind"] == "programme" and s["place_id"] in by_id and own:
            p = by_id[s["place_id"]]
            return f"{own['name']}: {p['title']}, {p['time']}"
        return s["place"]

    return {
        "today": today.isoformat(),
        "weekday": weekday,
        "indoor_only": rainy or hazy,
        "why_indoor": "rain" if rainy else "haze" if hazy else None,
        "psi": d.psi,
        "rain_mm": d.rain_mm,
        "likes": likes,
        # The engine places home at the senior's own AAC when it has one (only the postal sector is known),
        # so distances are "from their centre" in that case.
        "distance_from": "their centre" if own else "their area",
        "own_aac": ({"id": own["id"], "name": own["name"], "address": own.get("address"),
                     "programmes": [{k: p.get(k) for k in ("id", "title", "title_zh", "weekdays", "time", "tags", "indoor", "free", "sample", "fits")}
                                    | {"today": weekday in p["weekdays"], "hidden": p["id"] in hidden} for p in progs]}
                    if own else None),
        "nearby_aacs": near("aac", 3, {own["id"]} if own else set()),
        "nearby_ccs": near("cc", 3, set()),
        "suggested_today": [{"place": title_en(s), "kind": s["kind"], "why_it_fits": for_family(s), "indoor": s["indoor"],
                             "sample": s.get("sample", False), "as_told_to_senior": s["why_it_fits"]} for s in today_sugs],
        "suggestions": [{"id": s["id"], "date": s["date"], "place": s["place"], "kind": s["kind"], "why_it_fits": s["why_it_fits"],
                         "indoor": s["indoor"], "sample": s.get("sample", False),
                         "response": s.get("response") if responses else None} for s in sugs],
        "source": "AAC and CC locations: MOH Eldercare Services and PA Community Clubs on data.gov.sg (fetched 13 Oct 2026). "
                  "Programmes: entered by centre staff, or samples where none are entered.",
    }
