"""Places and suggestions. The senior's own AAC first, then the nearest community club.
Indoor only when it's raining or PSI > 100. Every "not for me" is remembered.

AAC programme timetables have no open feed: AAC staff enter them once in the AAC view
(stored as "programme" docs). The demo seeds sample programmes, marked sample: true.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache

from .data import FIXTURES, REGION_LABELS, _km, region_for_postal

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

SAMPLE_PROGRAMMES = [
    # title, title_zh, weekdays, time, tags, indoor
    ("Morning exercise", "早操", "mon wed fri", "8:30am", ["exercise", "walking"], True),
    ("Communal lunch", "一起吃午饭", "tue thu", "12pm", ["food", "chatting"], True),
    ("Karaoke", "卡拉OK", "wed sat", "10am", ["singing", "karaoke", "music"], True),
    ("Health talk", "健康讲座", "thu", "2pm", ["health", "learning"], True),
    ("Arts and crafts", "手工艺", "tue fri", "3pm", ["crafts", "art"], True),
    ("Mahjong and board games", "麻将和棋类", "mon thu sat", "2pm", ["mahjong", "games", "chatting"], True),
    ("Coffee-shop kopi meetup", "咖啡店聚会", "sat", "9am", ["kopi", "chatting", "men"], False),
]


@lru_cache(maxsize=1)
def places() -> list[dict]:
    return json.loads((FIXTURES / "places.json").read_text(encoding="utf-8"))["places"]


def place(place_id: str) -> dict | None:
    return next((p for p in places() if p["id"] == place_id), None)


def home_point(senior: dict) -> tuple[float, float]:
    own = place(senior.get("aac_id") or "")
    if own:
        return own["lat"], own["lon"]
    return REGION_LABELS[senior.get("region") or region_for_postal(senior.get("home_postal", ""))]


def sample_programmes(aac_id: str) -> list[dict]:
    return [{
        "id": f"prog-{aac_id}-{i}", "place_id": aac_id, "title": t, "title_zh": tz, "weekdays": wd.split(), "time": tm,
        "tags": tags, "indoor": indoor, "free": True, "sample": True,
    } for i, (t, tz, wd, tm, tags, indoor) in enumerate(SAMPLE_PROGRAMMES)]


def _fits(likes: list[str], tags: list[str]) -> str | None:
    likes_l = [l.lower() for l in likes]
    for tag in tags:
        for like in likes_l:
            if tag in like or like in tag:
                return like
    return None


def suggest(senior: dict, day: date, *, indoor_only: bool, programmes: list[dict] | None = None, limit: int = 3) -> list[dict]:
    """Up to `limit` options: programmes at the senior's own AAC that fit what they like, then the nearest CC."""
    zh = senior.get("language") == "zh"
    hidden = set(senior.get("hidden_suggestions", []))
    weekday = WEEKDAYS[day.weekday()]
    likes = senior.get("likes", [])
    out: list[dict] = []

    own = place(senior.get("aac_id") or "")
    own = own if own and own["kind"] == "aac" else None
    if own:
        progs = programmes if programmes is not None else sample_programmes(own["id"])
        ranked = sorted(
            (p for p in progs if weekday in p["weekdays"] and (p["indoor"] or not indoor_only)),
            key=lambda p: (_fits(likes, p["tags"]) is None, p["time"]),
        )
        for p in ranked:
            if p["id"] in hidden:
                continue
            like = _fits(likes, p["tags"])
            title = p.get("title_zh") if zh and p.get("title_zh") else p["title"]
            out.append({
                "place_id": p["id"], "place": f"{own['name']}: {title}, {p['time']}", "kind": "programme",
                "why_it_fits": (f"您喜欢{like}" if zh else f"You said you like {like}") if like else ("在您的活动中心" if zh else "At your own centre"),
                "indoor": p["indoor"], "free": p["free"], "sample": p.get("sample", False),
            })
            if len(out) >= limit - 1:
                break

    near = home_point(senior)
    ccs = sorted((p for p in places() if p["kind"] == "cc" and p["id"] not in hidden), key=lambda p: _km((p["lat"], p["lon"]), near))
    for cc in ccs[:1]:
        km = _km((cc["lat"], cc["lon"]), near)
        out.append({
            "place_id": cc["id"], "place": cc["name"], "kind": "cc",
            "why_it_fits": f"离家约{km:.1f}公里" if zh else f"About {km:.1f} km from home",
            "indoor": True, "free": True, "sample": False,
        })

    if not own:
        aacs = sorted((p for p in places() if p["kind"] == "aac" and p["id"] not in hidden), key=lambda p: _km((p["lat"], p["lon"]), near))
        for a in aacs[: limit - len(out)]:
            out.insert(0, {"place_id": a["id"], "place": a["name"], "kind": "aac",
                           "why_it_fits": "附近的乐龄活动中心" if zh else "Active Ageing Centre near you",
                           "indoor": True, "free": True, "sample": False})

    for i, s in enumerate(out[:limit]):
        s.update(id=f"sug-{senior['id']}-{day.isoformat()}-{i}", senior_id=senior["id"], date=day.isoformat(), response=None)
    return out[:limit]
