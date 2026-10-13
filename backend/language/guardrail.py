"""Guardrail on every outgoing message. A draft that breaks any rule is rejected and the fixed
template for that rung is sent instead.

Rejects a draft that:
  diagnosis           gives a diagnosis
  dose_change         changes or questions a dose
  stop_medicine       says to stop (or skip) a medicine
  calm_on_red_flag    sounds calm on a red flag (or lacks any call to act now)
  haze_go_out         says "wear a mask and go out", or sends the senior outdoors, during haze
  leads_with_number   opens with a number, to the senior
  invented_number     contains a number the senior never said and the engine never gave
  empty               says nothing at a rung that needs a message
"""
from __future__ import annotations

import re

from .facts import Audience, Facts, GuardrailResult, Rung
from .numbers import numbers_in

CONDITIONS_EN = (r"(?:a\s+)?(?:stroke|mini[- ]stroke|tia|heart attack|heart disease|heart failure|hypertensi\w+|high blood pressure|"
                 r"diabetes|infection|angina|arrhythmia|vertigo|anxiety|depression|dementia|covid|flu|\w+itis)")
CONDITIONS_ZH = r"(?:中风|脑中风|心脏病|心肌梗塞|心梗|高血压|糖尿病|感染|心绞痛|心律不齐|眩晕症|焦虑症|抑郁症|失智|痴呆|\S{0,3}炎)"

RULES: dict[str, list[str]] = {
    "diagnosis": [
        rf"\byou(?:'ve| have| might have| may have| probably have| could have| are having| might be having| may be having|'re having)\s+(?:got\s+)?{CONDITIONS_EN}\b",
        rf"\b(?:sounds|looks|seems)\s+like\s+{CONDITIONS_EN}\b", rf"\b(?:this|it)\s+(?:is|could be|might be|may be|is probably)\s+{CONDITIONS_EN}\b",
        r"\bdiagnos\w*", r"\bsymptoms? of\s+" + CONDITIONS_EN,
        rf"你(?:得了|患了|患有|有了|可能有|可能是|应该是|大概是)\S{{0,4}}{CONDITIONS_ZH}", rf"(?:是|像|可能是){CONDITIONS_ZH}(?:的症状|发作)?", r"诊断",
    ],
    "dose_change": [
        r"\b(?:take|took|have|eat|add)\s+(?:an?\s+)?(?:extra|another|more|less|fewer|half|double|two|2|one more|an additional)\s+(?:\w+\s+)?(?:pills?|tablets?|doses?|medicine|medication|meds)\b",
        r"\b(?:increase|reduce|lower|raise|double|halve|change|adjust|cut(?:\s+down)?)\s+(?:on\s+)?(?:your\s+|the\s+|this\s+)?(?:\w+\s+)?(?:dose|dosage|medicine|medication|meds|pills?)\b",
        r"\bdosage\b", r"\bhow many\s+(?:pills|tablets|mg|doses)\b", r"\b\d+\s*mg\b", r"\b(?:too much|too little|enough)\s+(?:medicine|medication|pills)\b",
        r"加药", r"减药", r"加量", r"减量", r"剂量", r"多吃一?[粒片颗]", r"少吃一?[粒片颗]", r"吃几[粒片颗]", r"半[粒片颗]", r"[两二三]\s*[粒片颗]", r"改.{0,3}药", r"换药",
    ],
    "stop_medicine": [
        r"\bstop(?:ping)?\s+(?:taking\s+|eating\s+)?(?:your\s+|the\s+|all\s+|this\s+)?(?:\w+\s+)?(?:medicine|medication|meds|pills?|tablets?)\b",
        r"\bno need (?:to )?(?:take|eat)\s+(?:your\s+|the\s+)?(?:medicine|medication|meds|pills?)\b",
        r"\bskip(?:ping)?\s+(?:your\s+|the\s+|a\s+)?(?:medicine|medication|meds|pills?|dose)\b",
        r"\b(?:don'?t|do not|no need to)\s+(?:take|eat)\s+(?:your\s+|the\s+|any\s+)?(?:medicine|medication|meds|pills?)\b",
        r"\b(?:come|go) off\s+(?:your\s+|the\s+)?(?:medicine|medication|meds|pills?)\b",
        r"停药", r"停止吃药", r"不用吃药", r"不要吃药", r"别吃药", r"先别吃", r"不吃药也", r"可以不吃",
    ],
}

CALM = [
    r"\bdon'?t worry\b", r"\bdo not worry\b", r"\bno need to worry\b", r"\bnothing to worry\b", r"\bnot to worry\b",
    r"\bshould be (?:fine|ok|okay|alright)\b", r"\bprobably (?:fine|nothing|ok|okay)\b", r"\bit'?s (?:fine|ok|okay|alright|nothing)\b",
    r"\bjust rest\b", r"\brest and see\b", r"\bwait and see\b", r"\bsee how (?:you|it) (?:feel|goes)\b", r"\bno big deal\b",
    r"\b(?:tomorrow|next week|at your next (?:visit|appointment))\b", r"\bnot urgent\b",
    r"不用担心", r"别担心", r"不要担心", r"没事", r"没关系", r"休息一下就好", r"应该没问题", r"观察一下", r"明天再", r"不急",
]
URGENT = [r"\b995\b", r"\bnow\b", r"\bimmediately\b", r"\bright away\b", r"\bemergency\b", r"马上", r"立刻", r"立即", r"现在", r"紧急", r"995"]

OUTDOORS = [
    r"\b(?:go|head|step|walk|jog|run)\s+(?:out|outside|outdoors)\b", r"\boutdoors?\b", r"\boutside\b", r"\bpark\b", r"\bpark connector\b",
    r"\b(?:go for|take) a (?:walk|jog|stroll)\b", r"\bexercise outside\b",
    r"出去", r"出门", r"外出", r"户外", r"公园", r"去散步", r"外面走",
]

# Numbers allowed in any message: the emergency number and the "rest 5 minutes, measure again" instruction.
ALWAYS_OK_NUMBERS = {995, 5}


def check(text: str, *, rung: Rung, to: Audience, facts: Facts, context: dict | None = None) -> GuardrailResult:
    context = context or {}
    reasons: list[str] = []
    t = text.strip()

    if not t:
        return GuardrailResult(passed=rung == "0", reasons=[] if rung == "0" else ["empty"])

    for rule, patterns in RULES.items():
        if any(re.search(p, t, re.I) for p in patterns):
            reasons.append(rule)

    # At rung R the message must call for action now. With red-flag facts at any rung, never reassure.
    if rung == "R" or facts.red_flag:
        calm = any(re.search(p, t, re.I) for p in CALM)
        urgent = any(re.search(p, t, re.I) for p in URGENT)
        if calm or (rung == "R" and not urgent):
            reasons.append("calm_on_red_flag")

    if _haze(context):
        if any(re.search(p, t, re.I) for p in OUTDOORS) and not _only_negated_outdoors(t):
            reasons.append("haze_go_out")

    if to == "senior" and re.match(r"^\W*\d", t):
        reasons.append("leads_with_number")

    allowed = facts.numbers() | ALWAYS_OK_NUMBERS | _context_numbers(context)
    if numbers_in(t) - allowed:
        reasons.append("invented_number")

    return GuardrailResult(passed=not reasons, reasons=reasons)


def _haze(context: dict) -> bool:
    psi = context.get("psi")
    try:
        if psi is not None and float(psi) > 100:
            return True
    except (TypeError, ValueError):
        pass
    return bool(context.get("haze"))


def _only_negated_outdoors(t: str) -> bool:
    """'Stay indoors, avoid going outside today' is the right advice, not a violation."""
    stripped = re.sub(r"\b(?:avoid|don'?t|do not|no|not|stay away from|better not)\s+(?:\w+\s+){0,2}?(?:going\s+)?(?:out|outside|outdoors|to the park)\b", "", t, flags=re.I)
    stripped = re.sub(r"(?:不要|别|避免|少)\S{0,2}(?:出去|出门|外出|户外|去公园)", "", stripped)
    return not any(re.search(p, stripped, re.I) for p in OUTDOORS)


def _context_numbers(context: dict) -> set[int]:
    out: set[int] = set()
    for v in context.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.add(int(v))
        elif isinstance(v, str):
            out |= numbers_in(v)
    return out
