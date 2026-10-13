"""Pull numbers out of what the senior said. Numbers are extracted, never rewritten or translated.

Handles digits ("145/90", "145 over 90") and spoken Mandarin numerals ("一百四十五").
"""
from __future__ import annotations

import re

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
CN_NUM = "[零〇一二两三四五六七八九十百千]+"
# A number token: digits, or a run of Mandarin numerals.
NUM = rf"(\d{{2,3}}|{CN_NUM})"


def cn_to_int(s: str) -> int | None:
    """一百四十五 -> 145, 九十 -> 90, 十二 -> 12, 一四五 -> 145 (digit by digit). None if not a number."""
    if not s or any(c not in CN_DIGITS and c not in CN_UNITS for c in s):
        return None
    if not any(c in CN_UNITS for c in s):
        return int("".join(str(CN_DIGITS[c]) for c in s))
    total, current = 0, 0
    for c in s:
        if c in CN_DIGITS:
            current = CN_DIGITS[c]
        else:
            unit = CN_UNITS[c]
            total += (current or 1) * unit  # 十二: implied 一
            current = 0
    return total + current


def to_int(token: str) -> tuple[int | None, float]:
    """A number token -> (value, confidence). Spoken Mandarin numerals are slightly less certain."""
    if token.isdigit():
        return int(token), 1.0
    v = cn_to_int(token)
    return v, 0.9


def plausible_bp(sys: int, dia: int) -> bool:
    return 60 <= sys <= 280 and 30 <= dia <= 160 and sys > dia


SEP = r"\s*(?:/|over|by|\\|除以|比|斜杠)\s*"


# Each pattern yields (systolic, diastolic[, pulse]) and a base confidence.
BP_PATTERNS: list[tuple[re.Pattern, float]] = [
    # "145/90", "145 over 90", "一百四十五除以九十"
    (re.compile(rf"{NUM}{SEP}{NUM}(?:\s*(?:pulse|hr|heart rate|心跳|脉搏)\s*(?:is|was|是)?\s*{NUM})?", re.I), 0.95),
    # "高压145低压90", "上面145下面90", "systolic 145 diastolic 90", "top 145 bottom 90"
    (re.compile(rf"(?:高压|上面|上压|收缩压|systolic|top|upper)\s*(?:is|was|是|有)?\s*{NUM}[,，\s]*(?:and\s*)?(?:低压|下面|下压|舒张压|diastolic|bottom|lower)\s*(?:is|was|是|有)?\s*{NUM}", re.I), 0.95),
    # "BP 145 90", "血压145 90", "pressure today 145, 90"
    (re.compile(rf"(?:bp|blood pressure|pressure|血压)\D{{0,12}}?{NUM}[\s,，、]+{NUM}", re.I), 0.75),
]

PULSE_RE = re.compile(rf"(?:pulse|heart rate|hr|心跳|脉搏)\s*(?:is|was|是|有)?\s*{NUM}", re.I)


def find_bp(text: str) -> list[dict]:
    """All BP readings in text: [{systolic, diastolic, pulse, confidence, span, plausible}].

    Confidence is lowered when the reading is ambiguous (bare numbers after "BP") or implausible
    (swapped, out of range). The trust check proper is the engine's job; this only flags.
    """
    found: list[dict] = []
    taken: list[tuple[int, int]] = []
    for pattern, base in BP_PATTERNS:
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            groups = [g for g in m.groups() if g]
            vals = [to_int(g) for g in groups]
            if any(v is None for v, _ in vals[:2]):
                continue
            sys, c1 = vals[0]
            dia, c2 = vals[1]
            pulse = vals[2][0] if len(vals) > 2 else None
            if sys < 50 and dia < 50:
                continue  # "13/10" is a date, "2 by 2" is not a reading
            conf = min(base, c1, c2)
            ok = plausible_bp(sys, dia)
            if not ok:
                conf = min(conf, 0.3)
            found.append({
                "systolic": sys, "diastolic": dia, "pulse": pulse,
                "confidence": round(conf, 2), "span": m.group(0).strip(), "plausible": ok,
            })
            taken.append((m.start(), m.end()))
    return found


def find_pulse(text: str) -> int | None:
    m = PULSE_RE.search(text)
    if not m:
        return None
    v, _ = to_int(m.group(1))
    return v


def numbers_in(text: str) -> set[int]:
    """Every number written in a piece of text, digits or Mandarin numerals."""
    out = {int(d) for d in re.findall(r"\d+", text)}
    for run in re.findall(CN_NUM, text):
        v = cn_to_int(run)
        # A lone 一/两 is usually "a"/"a couple", not a number worth guarding.
        if v is not None and len(run) > 1:
            out.add(v)
    return out
