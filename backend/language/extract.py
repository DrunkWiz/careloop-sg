"""Rule-based extraction. Always runs, with or without a model.

It is the floor: red-flag symptoms and every number come from here, so a model outage or a
model that misreads "I'm fine lah" can never hide a red flag. All three languages' patterns run
on every check-in, because seniors code-switch ("今天 BP 150 over 95, 有点头晕 lah").
"""
from __future__ import annotations

import re

from .facts import BP, Activity, Dose, Facts, Lang, Symptom, RED_FLAG_SYMPTOMS
from .numbers import find_bp, find_pulse

KNOWN_MEDICINES = (
    "amlodipine", "losartan", "lisinopril", "enalapril", "atenolol", "bisoprolol", "metoprolol",
    "hydrochlorothiazide", "hctz", "nifedipine", "valsartan", "telmisartan", "perindopril",
    "aspirin", "atorvastatin", "simvastatin", "metformin",
)
MED = r"(?:medicine|medicines|meds|medication|pills?|tablets?|ubat|" + "|".join(KNOWN_MEDICINES) + r")"

# English/Singlish negators within a few words before the symptom, or Mandarin 没(有)/不/无 right before it.
# Only filler words may sit between the negator and the symptom, so "don't know why, chest pain" stays a symptom.
NEG_FILLER = r"(?:have|has|had|got|any|feel|felt|feeling|some|more|much|a|the|my|any)"
NEG_EN = re.compile(rf"\b(?:no|not|without|never|don'?t|didn'?t|doesn'?t|isn'?t|nothing|no more)\b(?:\s+{NEG_FILLER}){{0,3}}\s*$", re.I)
NEG_ZH = re.compile(r"(?:没有|没|不|无|冇)[^，。,.!?！？]{0,2}$")

SYMPTOM_PATTERNS: dict[str, list[str]] = {
    "chest_pain": [
        r"chest\s*(?:pain|pains|tight|tightness|hurt|hurts|very pain|pain pain)",
        r"pain\w*\s+(?:in|at|on)\s+(?:my\s+)?chest", r"heart\s*(?:pain|very pain)", r"chest (?:feel|feels) (?:heavy|tight)",
        r"胸口痛", r"胸痛", r"胸闷", r"心口痛", r"胸口闷", r"心口闷",
    ],
    "face_droop": [
        r"face\s+(?:is\s+|feel\s+|feels\s+)?(?:droop\w*|crooked|senget|one side)", r"(?:droop\w*|crooked)\s+face",
        r"mouth\s+(?:is\s+)?(?:crooked|droop\w*|senget)", r"脸歪", r"嘴歪", r"面歪", r"口歪", r"面瘫",
    ],
    "slurred_speech": [
        r"slurr\w*", r"speech\s+(?:is\s+)?(?:funny|strange|unclear)", r"can(?:not|'t)\s+(?:talk|speak)\s+(?:properly|clearly|well)",
        r"talk(?:ing)?\s+(?:funny|cannot clear|not clear)", r"说话不清", r"讲话不清", r"口齿不清", r"说不出话", r"讲不出话",
    ],
    "one_sided_weakness": [
        r"(?:one|left|right)\s+(?:side|arm|leg|hand)\s+(?:\w+\s+){0,2}(?:weak|numb|no strength|no power|cannot move|can't move)",
        r"(?:weak|numb)\w*\s+(?:on|in)\s+(?:one|the left|the right|my left|my right)\s+side",
        r"一边[^，。,.]{0,4}(?:没力|无力|麻|不能动|动不了)", r"半边[^，。,.]{0,3}(?:没力|无力|麻|不能动)",
        r"(?:左|右)(?:手|脚|边)[^，。,.]{0,3}(?:没力|无力|麻|不能动|动不了)",
    ],
    "fainting": [
        r"faint(?:ed|ing)?\b", r"pass(?:ed)?\s+out", r"black(?:ed)?\s+out", r"pengsan", r"collapse[d]?",
        r"晕倒", r"昏倒", r"昏过去", r"晕过去",
    ],
    "headache": [r"headache", r"head\s*(?:pain|very pain|pain pain)", r"头痛", r"头疼"],
    "dizziness": [r"dizz\w*", r"giddy", r"giddiness", r"头晕", r"头昏"],
    "breathless": [r"breathless", r"short(?:ness)? of breath", r"can(?:not|'t) breathe", r"喘不过气", r"呼吸困难", r"气喘"],
    "palpitations": [r"palpitat\w*", r"heart\s+(?:beat\w*|beating)\s+(?:very\s+)?fast", r"心跳很快", r"心跳得很快", r"心慌"],
    "swelling": [r"(?:leg|legs|ankle|ankles|feet|foot)\s+(?:\w+\s+)?swell\w*", r"swollen\s+(?:leg|legs|ankle|ankles|feet)", r"脚肿", r"腿肿"],
    "tired": [r"\btired\b", r"no energy", r"\bsian\b", r"很累", r"好累", r"没精神", r"没力气"],
    "unwell": [r"\bunwell\b", r"not (?:feeling )?(?:so )?(?:well|good)", r"feel(?:ing)? (?:sick|not ok)", r"不舒服", r"不太舒服", r"身体不好"],
}

DOSE_TAKEN = [
    rf"(?:took|taken|take(?:n)? already|ate|eat(?:en)?|swallow(?:ed)?)\s+(?:my\s+|the\s+|all\s+(?:my\s+)?)?(?:morning\s+|night\s+)?{MED}",
    rf"{MED}\s+(?:\w+\s+)?(?:taken|eaten|eat already|take already|already take|already eat|done)",
    r"吃了药", r"吃过药", r"药吃了", r"药已经吃了", r"吃药了", r"吃完药",
]
DOSE_MISSED = [
    rf"(?:forgot|forget|forgotten)\s+(?:to\s+)?(?:take|eat)?\s*(?:my\s+|the\s+)?{MED}",
    rf"(?:didn'?t|did not|never|haven'?t|have not|not yet)\s+(?:take|eat|taken|eaten)\s+(?:my\s+|the\s+)?{MED}",
    rf"miss(?:ed)?\s+(?:my\s+|a\s+|the\s+)?(?:dose|{MED})", rf"skip(?:ped)?\s+(?:my\s+)?{MED}",
    r"忘了吃药", r"忘记吃药", r"没吃药", r"没有吃药", r"还没吃药", r"药没吃", r"漏吃",
]
RUNNING_OUT = [
    rf"{MED}\s+(?:\w+\s+){{0,2}}(?:running out|run out|almost (?:finish|finished|gone)|finish(?:ed)? already|left (?:\w+ )?(?:day|days|pill|pills))",
    rf"(?:running|run|ran)\s+out\s+of\s+(?:my\s+)?{MED}", rf"no more\s+{MED}", rf"(?:need|must|have) to\s+(?:get|collect|refill)\s+(?:more\s+|my\s+)?{MED}",
    r"refill", r"药快(?:要)?吃完", r"药吃完了", r"没药了", r"药不够", r"要去拿药", r"药快没了",
]

ACTIVITY_PATTERNS: list[tuple[str, bool, list[str]]] = [
    ("social", True, [
        r"mahjong", r"kopi\s+with", r"(?:with|meet|met|see|saw|visit\w*)\s+(?:my\s+)?(?:friends?|kakis?|neighbou?rs?|grand\w+|son|daughter|family)",
        r"\bAAC\b", r"active ageing", r"community cent(?:re|er)", r"\bCC\b", r"church", r"temple", r"karaoke", r"\bsing(?:ing)?\b",
        r"打麻将", r"搓麻将", r"朋友", r"邻居", r"孙子", r"孙女", r"活动中心", r"乐龄", r"教堂", r"拜神", r"唱歌", r"喝咖啡",
    ]),
    ("exercise", False, [
        r"\bwalk(?:ed|ing)?\b", r"exercis\w*", r"tai\s*chi", r"taiji", r"qigong", r"\bswim\w*", r"\bgym\b",
        r"散步", r"运动", r"太极", r"气功", r"游泳", r"走路",
    ]),
    ("outing", False, [r"market", r"pasar", r"hawker", r"kopitiam", r"food cent(?:re|er)", r"巴刹", r"菜市场", r"买菜", r"小贩中心"]),
    ("home", False, [r"stay(?:ed)?\s+(?:at\s+)?home", r"never\s+go\s+out", r"didn'?t\s+go\s+out", r"whole day (?:at )?home", r"在家", r"没出门", r"没有出门"]),
]

MOOD_PATTERNS: list[tuple[str, list[str]]] = [
    ("low", [r"\bsad\b", r"lonely", r"\bbored\b", r"\bsian\b", r"\bmoody\b", r"不开心", r"(?<!胸)(?<!口)闷", r"孤单", r"寂寞", r"难过", r"心情不好"]),
    ("good", [r"\bhappy\b", r"\bshiok\b", r"\bgreat\b", r"\bgood\b", r"\bfine\b", r"\bok(?:ay)?\b", r"开心", r"很好", r"不错", r"高兴", r"还好", r"没事"]),
]

SINGLISH_MARKERS = re.compile(r"\b(?:lah|leh|lor|meh|sia|liao|walao|alamak|shiok|sian|can or not|already lah|pengsan|kopi|makan|kakis?|paiseh|abuden|can lah)\b", re.I)


def detect_lang(text: str) -> Lang:
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk and cjk * 2 >= latin:
        return "zh"
    if SINGLISH_MARKERS.search(text):
        return "en-SG"
    return "en"


def _negated(text: str, start: int) -> bool:
    before = text[max(0, start - 30):start]
    return bool(NEG_EN.search(before) or NEG_ZH.search(before))


def _matches(patterns: list[str], text: str):
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            yield m


def extract(text: str, lang: Lang | None = None) -> Facts:
    lang = lang or detect_lang(text)
    facts = Facts(lang=lang, english=text if lang in ("en", "en-SG") else "")

    readings = find_bp(text)
    for r in readings:
        facts.bp.append(BP(**r))
    pulse = find_pulse(text)
    if pulse is not None and not any(b.pulse == pulse for b in facts.bp):
        facts.pulse = pulse

    seen: set[str] = set()
    for code, patterns in SYMPTOM_PATTERNS.items():
        for m in _matches(patterns, text):
            if code in seen or _negated(text, m.start()):
                continue
            facts.symptoms.append(Symptom(code=code, words=m.group(0), red_flag=code in RED_FLAG_SYMPTOMS))
            seen.add(code)

    missed_spans = []
    for m in _matches(DOSE_MISSED, text):
        facts.doses.append(Dose(taken=False, medicine=_medicine_in(m.group(0)), span=m.group(0)))
        missed_spans.append((m.start(), m.end()))
    for m in _matches(DOSE_TAKEN, text):
        if any(m.start() < e and s < m.end() for s, e in missed_spans) or _negated(text, m.start()):
            continue
        facts.doses.append(Dose(taken=True, medicine=_medicine_in(m.group(0)), span=m.group(0)))
        break  # one "took my pills" is enough

    for m in _matches(RUNNING_OUT, text):
        name = _medicine_in(m.group(0)) or "unspecified"
        if name not in facts.running_out:
            facts.running_out.append(name)

    for kind, social, patterns in ACTIVITY_PATTERNS:
        for m in _matches(patterns, text):
            if _negated(text, m.start()) and kind != "home":
                continue
            facts.activities.append(Activity(kind=kind, words=m.group(0), social_contact=social))
            break

    for mood, patterns in MOOD_PATTERNS:
        if any(not _negated(text, m.start()) for m in _matches(patterns, text)):
            facts.mood = mood
            break

    return facts


def _medicine_in(span: str) -> str | None:
    low = span.lower()
    for name in KNOWN_MEDICINES:
        if name in low:
            return name
    return None
