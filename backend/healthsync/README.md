# backend/healthsync

Health data from the senior's phone: **Apple Health** on an iPhone, **Health Connect** on Android.

Owner: Nathan

## Why

A Fitbit syncs to both, through the Fitbit app (renamed Google Health in May 2026). So does a home BP
cuff such as OMRON's, through OMRON connect. With them connected, steps, resting heart rate, sleep and
BP arrive without the senior typing anything in. Fitbit doesn't measure BP; the cuff does.

A web page can't read either store: only an app installed on the phone can. The plan is a small CareLoop
phone app that reads the day's records and posts them to `POST /senior/{id}/health-sync`. **That app isn't
built.** `simulate.py` stands in for it, in the demo and in tests.

## What it does

- `mapping.py`: records as each platform hands them over (Health Connect `StepsRecord`,
  `RestingHeartRateRecord`, `SleepSessionRecord`, `BloodPressureRecord`; HealthKit `HKQuantitySample`,
  `HKCategorySample`, `HKCorrelation`) become CareLoop readings. Numbers are carried over, never changed;
  a sample in an unexpected unit is skipped, not converted. Other record types (weight, say) are skipped
  and counted.
- `ingest.py`: stores them. Steps come in hourly blocks and are merged by record id with what earlier syncs
  sent, so a phone can send the whole day again or only what's new, and nothing counts twice. Steps, heart
  rate and sleep get one reading a day with a fixed id (`hs-{senior}-steps-{date}`), so each sync replaces
  the last. Each BP measurement is its own reading (source `cuff`). Every reading passes the trust check;
  a record from the future (a wrong phone clock) is skipped. What's connected and when it last synced is
  kept per senior.
- `simulate.py`: one day of synthetic Fitbit and OMRON records in either platform's shape.

The API runs the engine for today after a sync that touches today, the same as after any reading. So a
synced 186/112 from the cuff is a red flag at once, with nothing said or typed.

## In the demo

Five of the twelve demo seniors have a phone that syncs (`DEVICES` in `backend/api/demo.py`). In the family
app's Health tab and the centre console's senior page, the "Health apps" card shows what's connected and
the last seven days; its demo buttons sync now or send a cuff measurement.

```
python -m unittest discover -s backend/healthsync/tests -t .
```

`fixtures/` holds a hand-written morning from each platform (synthetic), used by the tests.
