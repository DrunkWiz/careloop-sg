"""Import a centre's timetable from what it already keeps: a calendar (.ics, as Google Calendar or Outlook
export it, or a calendar link) or a spreadsheet (.csv). Weekly events become programmes.

There is no open feed of AAC or CC programmes (data.gov.sg has their locations only), so this is the
quickest way to get a real timetable in without retyping it. Tags and indoor or outdoor are guessed from
the title, so suggestions can match what each senior likes; staff can change them afterwards.
Standard library only. No model: the guesses are keyword rules, and every guess is shown before saving.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))
WEEK = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
BYDAY = {"MO": "mon", "TU": "tue", "WE": "wed", "TH": "thu", "FR": "fri", "SA": "sat", "SU": "sun"}

# Keyword -> tags. Tags are the words seniors' likes use (see backend/env/places.py SAMPLE_PROGRAMMES).
TAGS = [
    (("exercise", "fitness", "zumba", "yoga", "qigong", "taiji", "tai chi", "stretch", "aerobic", "line danc", "workout", "早操", "运动", "太极"), ["exercise"]),
    (("walk", "brisk", "stroll", "健走"), ["walking", "exercise"]),
    (("karaoke", "sing", "choir", "song", "卡拉", "唱"), ["singing", "karaoke", "music"]),
    (("music", "drum", "ukulele", "音乐"), ["music"]),
    (("mahjong", "麻将"), ["mahjong", "games", "chatting"]),
    (("bingo", "board game", "games", "chess", "rummikub", "cards", "棋", "游戏"), ["games", "chatting"]),
    (("craft", "art", "paint", "draw", "knit", "sew", "calligraphy", "手工", "书法", "画"), ["crafts", "art"]),
    (("lunch", "breakfast", "meal", "cook", "baking", "kopi", "coffee", "tea", "午饭", "早餐", "咖啡"), ["food", "chatting"]),
    (("kopi", "coffee"), ["kopi"]),
    (("health", "talk", "screening", "seminar", "workshop", "dementia", "medication", "讲座", "健康"), ["health", "learning"]),
    (("garden", "plant", "园艺"), ["gardening"]),
    (("digital", "smartphone", "phone", "computer", "ipad", "whatsapp", "手机"), ["learning"]),
    (("befriend", "chat", "tea session", "social", "gathering", "聊天"), ["chatting"]),
    (("outing", "trip", "excursion", "visit to", "郊游"), ["outing", "chatting"]),
    (("dance", "danc", "跳舞"), ["exercise", "music"]),
]
OUTDOOR = ("walk", "outing", "trip", "excursion", "park", "garden", "hike", "jog", "cycling", "beach", "outdoor", "公园", "郊游")
INDOOR_HINT = ("indoor", "hall", "void deck", "centre", "center", "room", "室内")
FEE = re.compile(r"(\$\s?\d|\bfee\b|\bpaid\b|\bS\$|收费)", re.I)


def guess(title: str, more: str = "") -> tuple[list[str], bool, bool]:
    """Tags, indoor and free, from the title (and description or location, if any)."""
    t = f"{title} {more}".lower()
    tags: list[str] = []
    for words, add in TAGS:
        if any(w in t for w in words):
            tags += [x for x in add if x not in tags]
    indoor = not any(w in t for w in OUTDOOR) or any(w in t for w in INDOOR_HINT)
    return tags, indoor, not FEE.search(t)


def fmt_time(h: int, m: int) -> str:
    """Times as the rest of CareLoop writes them: 8:30am, 2pm, 12pm."""
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{f':{m:02d}' if m else ''}{suffix}"


def parse_time(s: str) -> str | None:
    s = s.strip().lower().replace(".", ":").replace(" ", "")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?(am|pm)?", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h < 24 and 0 <= mi < 60):
        return None
    return fmt_time(h, mi)


def parse_days(s: str) -> list[str]:
    s = s.strip().lower()
    if not s:
        return []
    if s in ("daily", "every day", "everyday", "每天"):
        return list(WEEK)
    if s in ("weekdays", "mon-fri", "monday to friday", "平日"):
        return list(WEEK[:5])
    if s in ("weekends", "weekend", "sat-sun", "周末"):
        return ["sat", "sun"]
    out: list[str] = []
    for part in re.split(r"[,/&;]|\band\b", s):
        part = part.strip()
        rng = re.match(r"^([a-z]{3})[a-z]*\s*(?:-|to)\s*([a-z]{3})[a-z]*$", part)
        if rng and rng.group(1) in WEEK and rng.group(2) in WEEK:
            a, b = WEEK.index(rng.group(1)), WEEK.index(rng.group(2))
            out += [WEEK[i % 7] for i in range(a, a + ((b - a) % 7) + 1)]
        elif part[:3] in WEEK:
            out.append(part[:3])
    return sorted(set(out), key=WEEK.index)


def _programme(title: str, weekdays: list[str], time: str, more: str = "", title_zh: str | None = None,
               indoor: bool | None = None, free: bool | None = None, tags: list[str] | None = None) -> dict:
    g_tags, g_indoor, g_free = guess(title + " " + (title_zh or ""), more)
    return {"title": title.strip(), "title_zh": title_zh or None, "weekdays": weekdays, "time": time,
            "tags": tags or g_tags, "indoor": g_indoor if indoor is None else indoor, "free": g_free if free is None else free}


def _merge(progs: list[dict]) -> list[dict]:
    """The same programme at the same time on several days (common in exports) becomes one."""
    out: dict[tuple[str, str], dict] = {}
    for p in progs:
        k = (p["title"].lower(), p["time"])
        if k in out:
            out[k]["weekdays"] = sorted(set(out[k]["weekdays"]) | set(p["weekdays"]), key=WEEK.index)
        else:
            out[k] = p
    return sorted(out.values(), key=lambda p: (WEEK.index(p["weekdays"][0]), p["time"]))


# --- .ics ------------------------------------------------------------------------------------

def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw:
            lines.append(raw)
    return lines


def _unescape(v: str) -> str:
    return v.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _dt(value: str, params: str) -> datetime | date | None:
    v = value.strip()
    try:
        if "VALUE=DATE" in params.upper() or re.fullmatch(r"\d{8}", v):
            return datetime.strptime(v[:8], "%Y%m%d").date()
        if v.endswith("Z"):
            return datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(SGT)
        return datetime.strptime(v[:15], "%Y%m%dT%H%M%S")  # floating or TZID: centres in Singapore use local time
    except ValueError:
        return None


def from_ics(text: str, *, today: date | None = None) -> tuple[list[dict], list[str]]:
    progs: list[dict] = []
    warnings: list[str] = []
    ev: dict[str, tuple[str, str]] | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            ev = {}
            continue
        if line == "END:VEVENT" and ev is not None:
            title = _unescape(ev.get("SUMMARY", ("", ""))[1]).strip()
            start = _dt(ev["DTSTART"][1], ev["DTSTART"][0]) if "DTSTART" in ev else None
            rrule = dict(kv.split("=", 1) for kv in ev.get("RRULE", ("", ""))[1].split(";") if "=" in kv)
            more = " ".join(_unescape(ev.get(k, ("", ""))[1]) for k in ("DESCRIPTION", "LOCATION"))
            ev = None
            if not title:
                continue
            if not rrule:
                warnings.append(f"“{title}” happens once, so it isn't a weekly programme. Skipped.")
                continue
            if not isinstance(start, datetime):
                warnings.append(f"“{title}” has no start time (an all-day event). Skipped.")
                continue
            until = _dt(rrule["UNTIL"], "") if "UNTIL" in rrule else None
            until_d = until.date() if isinstance(until, datetime) else until
            if today and until_d and until_d < today:
                warnings.append(f"“{title}” ended on {until_d:%d %b %Y}. Skipped.")
                continue
            freq = rrule.get("FREQ", "")
            if freq == "WEEKLY":
                days = [BYDAY[d[-2:]] for d in rrule.get("BYDAY", "").split(",") if d[-2:] in BYDAY] or [WEEK[start.weekday()]]
            elif freq == "DAILY":
                days = [BYDAY[d[-2:]] for d in rrule.get("BYDAY", "").split(",") if d[-2:] in BYDAY] or list(WEEK)
            else:
                warnings.append(f"“{title}” repeats {freq.lower() or 'irregularly'}, not weekly. Skipped.")
                continue
            if rrule.get("INTERVAL", "1") != "1":
                warnings.append(f"“{title}” runs every {rrule['INTERVAL']} weeks; imported as weekly, so check it.")
            progs.append(_programme(title, sorted(set(days), key=WEEK.index), fmt_time(start.hour, start.minute), more))
            continue
        if ev is not None and ":" in line:
            head, value = line.split(":", 1)
            name, _, params = head.partition(";")
            ev.setdefault(name.upper(), (params, value))
    if not progs and not warnings:
        warnings.append("No events found in this calendar.")
    return _merge(progs), warnings


# --- .csv ------------------------------------------------------------------------------------

COLS = {
    "title": ("title", "programme", "program", "activity", "name", "event"),
    "title_zh": ("title_zh", "chinese", "中文", "中文名称"),
    "days": ("days", "day", "weekdays", "weekday", "when"),
    "time": ("time", "start", "start time", "starts"),
    "indoor": ("indoor", "indoor/outdoor", "venue type", "where"),
    "free": ("free", "fee", "cost", "price"),
    "tags": ("tags", "type", "category"),
}


def from_csv(text: str) -> tuple[list[dict], list[str]]:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows:
        return [], ["The file is empty."]
    head = [h.strip().lower() for h in rows[0]]
    col = {k: next((i for i, h in enumerate(head) if h in names), None) for k, names in COLS.items()}
    if col["title"] is None or col["days"] is None or col["time"] is None:
        return [], ["The first row needs columns for the programme, the days and the time (for example: Programme, Days, Time)."]
    progs, warnings = [], []
    cell = lambda r, k: r[col[k]].strip() if col[k] is not None and col[k] < len(r) else ""
    for n, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        title, days, time = cell(r, "title"), parse_days(cell(r, "days")), parse_time(cell(r, "time"))
        if not title or not days or not time:
            warnings.append(f"Row {n} skipped: it needs a programme, days and a time.")
            continue
        io_cell, fee_cell = cell(r, "indoor").lower(), cell(r, "free").lower()
        indoor = None if not io_cell else io_cell.startswith(("y", "in", "室内"))
        if fee_cell in ("", "-"):
            free = None
        elif fee_cell in ("yes", "y", "free", "0", "$0", "no fee", "免费"):
            free = True
        else:
            free = False
        tags = [t.strip().lower() for t in re.split(r"[;,]", cell(r, "tags")) if t.strip()] or None
        progs.append(_programme(title, days, time, title_zh=cell(r, "title_zh") or None, indoor=indoor, free=free, tags=tags))
    return _merge(progs), warnings


def parse(text: str, *, today: date | None = None) -> tuple[list[dict], list[str]]:
    if "BEGIN:VCALENDAR" in text[:2000].upper():
        return from_ics(text, today=today)
    return from_csv(text)
