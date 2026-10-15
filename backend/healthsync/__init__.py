"""Health data from the senior's phone: Apple Health (iPhone) and Health Connect (Android).

A Fitbit syncs to both, through the Fitbit (now Google Health) app. So does a home BP cuff such as Omron's.
A small CareLoop app on the senior's phone would read the day's records and post them to
`POST /senior/{id}/health-sync`. That phone app isn't built: `simulate.py` stands in for it.
"""
from .ingest import ingest, status
from .mapping import PLATFORMS, parse, to_readings

__all__ = ["PLATFORMS", "parse", "to_readings", "ingest", "status"]
