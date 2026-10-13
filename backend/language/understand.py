"""understand(text, lang) -> Facts.

Rules run first and always. The model, when one answers, may only ADD meaning the rules missed
(a symptom said in a roundabout way, the mood, an English gloss). It can never remove what the
rules found, and it can never introduce a number: a BP the model reports is kept only if both
numbers literally appear in what the senior said, and then only at low confidence so the senior
app asks the senior to confirm it.
"""
from __future__ import annotations

import json

from .extract import extract
from .facts import BP, Activity, Dose, Facts, Lang, Symptom, SYMPTOM_CODES, RED_FLAG_SYMPTOMS
from .gateway import Chain, Gateway, ModelError, as_chain
from .numbers import numbers_in, plausible_bp

SYSTEM = """You read a short check-in from an older Singaporean with high blood pressure.
They may speak English, Singlish or Mandarin, and may mix them.
Return ONLY a JSON object with these keys:
  "english": the meaning in plain English (keep every number exactly as said),
  "symptoms": list of {"code": one of %s, "words": the person's own words},
  "activities": list of {"kind": "social"|"exercise"|"outing"|"home", "words": their words},
  "doses": list of {"taken": true|false, "medicine": name or null},
  "running_out": list of medicine names, or ["unspecified"],
  "mood": "good"|"ok"|"low"|null,
  "bp": list of {"systolic": n, "diastolic": n} ONLY if the person said the numbers.
Singlish: "eat medicine" = took medicine; "pengsan" = fainted; "giddy" = dizzy; "sian" = bored/low;
"heart pain" = chest pain; "never take" = did not take.
Do not judge whether anything is dangerous. Do not give advice. Do not guess numbers.""" % (list(SYMPTOM_CODES),)


def understand(text: str, lang: Lang | None = None, *, gateway: Gateway | Chain | None = None) -> Facts:
    facts = extract(text, lang)
    if not text.strip():
        return facts
    chain = as_chain(gateway)
    if not chain.rungs:
        return facts
    try:
        raw, used = chain.complete(SYSTEM, f"Language hint: {facts.lang}\nCheck-in: {text}",
                                   want_json=True, accept=_parses)
    except ModelError:
        return facts
    _merge(facts, _parse(raw), text)
    facts.source = f"rules+model:{used}"
    return facts


def _parses(raw: str) -> bool:
    try:
        return isinstance(_parse(raw), dict)
    except ValueError:
        return False


def _parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object")
    return json.loads(raw[start:end + 1])


def _merge(facts: Facts, m: dict, text: str) -> None:
    if isinstance(m.get("english"), str) and m["english"].strip():
        facts.english = m["english"].strip()

    have = {s.code for s in facts.symptoms}
    for s in _list(m.get("symptoms")):
        code = s.get("code") if isinstance(s, dict) else None
        if code in SYMPTOM_CODES and code not in have:
            facts.symptoms.append(Symptom(code=code, words=str(s.get("words") or ""), red_flag=code in RED_FLAG_SYMPTOMS))
            have.add(code)

    kinds = {a.kind for a in facts.activities}
    for a in _list(m.get("activities")):
        kind = a.get("kind") if isinstance(a, dict) else None
        if kind in ("social", "exercise", "outing", "home") and kind not in kinds:
            facts.activities.append(Activity(kind=kind, words=str(a.get("words") or ""), social_contact=kind == "social"))
            kinds.add(kind)

    if not facts.doses:
        for d in _list(m.get("doses")):
            if isinstance(d, dict) and isinstance(d.get("taken"), bool):
                facts.doses.append(Dose(taken=d["taken"], medicine=d.get("medicine") or None, span=""))

    for name in _list(m.get("running_out")):
        if isinstance(name, str) and name and name not in facts.running_out:
            facts.running_out.append(name)

    if facts.mood is None and m.get("mood") in ("good", "ok", "low"):
        facts.mood = m["mood"]

    # Numbers: only ones the senior actually said, and never at high confidence.
    said = numbers_in(text)
    known = {(b.systolic, b.diastolic) for b in facts.bp}
    for b in _list(m.get("bp")):
        try:
            sys, dia = int(b["systolic"]), int(b["diastolic"])
        except (TypeError, KeyError, ValueError):
            continue
        if (sys, dia) in known or sys not in said or dia not in said:
            continue
        facts.bp.append(BP(systolic=sys, diastolic=dia, confidence=0.5, span="", plausible=plausible_bp(sys, dia)))
        known.add((sys, dia))


def _list(v) -> list:
    return v if isinstance(v, list) else []
