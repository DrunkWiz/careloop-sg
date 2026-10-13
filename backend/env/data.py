"""PSI and rainfall from data.gov.sg, with offline fixtures. Tests never hit the network."""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

FIXTURES = Path(__file__).with_name("fixtures")
API = "https://api-open.data.gov.sg/v2/real-time/api"
UA = {"User-Agent": "careloop-sg/0.1 (hackathon)"}

# Postal sector (first 2 digits) -> NEA PSI region. Approximate: built from URA postal districts,
# then each district placed in the PSI region whose label location is nearest.
_SECTOR_REGION: dict[str, str] = {}
for region, sectors in {
    "south": "07 08 09 10 14 15 16 26 27 34 35",
    "central": "01 02 03 04 05 06 11 12 13 17 18 19 20 21 22 23 24 25 28 29 30 31 32 33 57 58 59",
    "east": "36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 81",
    "north": "53 54 55 56 72 73 75 76 77 78 79 80 82",
    "west": "60 61 62 63 64 65 66 67 68 69 70 71",
}.items():
    for s in sectors.split():
        _SECTOR_REGION[s] = region

REGION_LABELS = {  # NEA PSI region label locations (from the PSI API metadata)
    "north": (1.41803, 103.82), "south": (1.29587, 103.82), "east": (1.35735, 103.94),
    "west": (1.35735, 103.70), "central": (1.35735, 103.82),
}


def region_for_postal(postal: str) -> str:
    return _SECTOR_REGION.get((postal or "")[:2], "central")


def _get(path: str, params: dict) -> dict:
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        return json.load(r)


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def parse_psi(payload: dict, region: str) -> int | None:
    items = (payload.get("data") or {}).get("items") or []
    if not items:
        return None
    return items[-1]["readings"]["psi_twenty_four_hourly"].get(region)


def parse_rainfall(payloads: list[dict], near: tuple[float, float]) -> float | None:
    """Total mm over the payloads' 5-minute readings at the station nearest `near`."""
    if not payloads:
        return None
    stations = {s["id"]: (s["location"]["latitude"], s["location"]["longitude"])
                for p in payloads for s in (p.get("data") or {}).get("stations", [])}
    if not stations:
        return None
    sid = min(stations, key=lambda k: _km(stations[k], near))
    total = 0.0
    for p in payloads:
        for r in (p.get("data") or {}).get("readings", []):
            total += sum(x["value"] for x in r["data"] if x["stationId"] == sid)
    return round(total, 1)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def envday(day: date, region: str, *, psi: int | None, rainfall_mm: float | None, source: str = "synthetic",
           forecast: str | None = None) -> dict:
    from backend.engine.config import festival_on

    return {
        "id": f"env-{day.isoformat()}-{region}", "date": day.isoformat(), "region": region,
        "psi_24h": psi, "rainfall_mm": rainfall_mm, "forecast": forecast, "festival": festival_on(day), "source": source,
    }


def fetch_envday(day: date, region: str, *, live: bool = False) -> dict:
    """EnvDay for a region. Offline (default): the newest fixture. Live: data.gov.sg for that date."""
    near = REGION_LABELS[region]
    if not live:
        psi_p = fixture("psi_2026-10-13.json")
        rain_p = fixture("rainfall_2026-10-13.json")
        return envday(day, region, psi=parse_psi(psi_p, region), rainfall_mm=parse_rainfall([rain_p], near), source="fixture")
    psi_p = _get("psi", {"date": day.isoformat()})
    pages, token = [], None
    for _ in range(400):  # a day is 288 five-minute readings; the API pages them
        params = {"date": day.isoformat(), **({"paginationToken": token} if token else {})}
        p = _get("rainfall", params)
        pages.append(p)
        token = (p.get("data") or {}).get("paginationToken")
        if not token:
            break
    return envday(day, region, psi=parse_psi(psi_p, region), rainfall_mm=parse_rainfall(pages, near), source="data.gov.sg")
