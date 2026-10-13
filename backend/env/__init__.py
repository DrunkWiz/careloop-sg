"""Environment: haze (NEA 24-hour PSI by region), rain (NEA rainfall by station), places
(MOH eldercare services, PA community clubs), all from data.gov.sg.

Tests and the demo use the offline fixtures in fixtures/. Live calls happen only in
fetch_envday(..., live=True), which the API's daily job uses when CARELOOP_LIVE_ENV=1.
"""
from .data import envday, fetch_envday, region_for_postal
from .places import suggest, places, place

__all__ = ["envday", "fetch_envday", "region_for_postal", "suggest", "places", "place"]
