"""The one place thresholds live. Red-flag floors are PLACEHOLDER until clinical sign-off."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

T: dict = json.loads((Path(__file__).with_name("thresholds.json")).read_text(encoding="utf-8"))

# MOH haze advisory, keyed by 24-hour PSI band. Wording is fixed; the model never writes haze advice.
# (band, upper PSI inclusive, English, Mandarin)
HAZE_BANDS = [
    ("good", 100, "", ""),
    ("unhealthy", 200,
     "The air is unhealthy today. Cut down on long or hard activity outdoors. An indoor option may suit you today. Keep your medicines handy.",
     "今天空气不好。请减少长时间或费力的户外活动。今天可以选室内的活动。药放在身边。"),
    ("very_unhealthy", 300,
     "Better to stay in today. If you must be out for hours, an N95 mask can help, but ask your doctor first if breathing is hard for you.",
     "今天最好待在家里。如果一定要在外面几个小时，N95 口罩有帮助，但如果您呼吸困难，请先问医生。"),
    ("hazardous", 10_000,
     "Please stay indoors today. Your family or Active Ageing Centre has been told.",
     "今天请待在室内。已经通知您的家人或乐龄活动中心。"),
]


def haze_band(psi: int | None) -> tuple[str, str, str]:
    """(band, english, mandarin). Below 101 there is nothing to say."""
    if psi is None:
        return ("unknown", "", "")
    for band, upper, en, zh in HAZE_BANDS:
        if psi <= upper:
            return (band, en, zh)
    return HAZE_BANDS[-1][0], HAZE_BANDS[-1][2], HAZE_BANDS[-1][3]


# Festivals that move readings (rich food, late nights, travel). First day of each.
FESTIVALS: dict[str, list[date]] = {
    "Chinese New Year": [date(2026, 2, 17), date(2027, 2, 6)],
    "Hari Raya Puasa": [date(2026, 3, 21), date(2027, 3, 10)],
    "Deepavali": [date(2026, 11, 8), date(2027, 10, 28)],
    "Christmas": [date(2026, 12, 25), date(2027, 12, 25)],
}


def festival_on(d: date) -> str | None:
    w = T["festival_window_days"]
    for name, days in FESTIVALS.items():
        for f in days:
            if -1 <= (d - f).days <= w:
                return name
    return None
