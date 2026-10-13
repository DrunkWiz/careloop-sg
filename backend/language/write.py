"""write(rung, facts, lang) -> Message.

The engine has already chosen the rung; this only chooses words. The model drafts in the senior's
language and tone inside that rung. The guardrail checks every draft; a draft that fails, or no
model at all, means the fixed template for the rung goes out instead.
"""
from __future__ import annotations

import json

from .facts import Audience, Facts, GuardrailResult, Lang, Message, Rung
from .gateway import Chain, Gateway, ModelError, as_chain
from .guardrail import check
from . import templates

RUNG_MEANING = {
    "1": "ASK: gently ask how they are and, if useful, invite them to take a BP reading. One question.",
    "2": "SUGGEST: offer the one suggestion in the context (a place or activity). Easy to say no to.",
    "3": "NOTE IN DIGEST: one factual line for the family's weekly digest.",
    "4": "HAND OVER: tell the family/AAC worker plainly what CareLoop saw and that the evidence is in the app.",
    "R": "RED FLAG: urgent. Tell them to act NOW (call 995 for danger symptoms). Never reassure.",
}

LANG_NAME = {"en": "plain English", "en-SG": "warm, simple English a Singaporean senior would use (light Singlish is fine)", "zh": "简体中文，口语化、亲切"}

SYSTEM = """You write one short message for CareLoop, which supports older Singaporeans with high blood pressure.
The rung (what kind of message) is already decided. Write ONLY the message text, nothing else.
Hard rules:
- Never diagnose. Never mention a dose, never suggest changing, skipping or stopping a medicine.
- Never start a message to the senior with a number. Use only numbers given to you; never invent one.
- On a red flag, never reassure: tell them to act now.
- During haze, never suggest going outdoors, with or without a mask.
- At most 3 short sentences. No emoji."""


def write(rung: Rung, facts: Facts, lang: Lang | None = None, *, to: Audience = "senior",
          context: dict | None = None, gateway: Gateway | Chain | None = None) -> Message:
    lang = lang or facts.lang
    context = context or {}
    template = templates.render(rung, to, facts, lang, context)

    if rung == "0" or not template:
        # Rung 0 says nothing; nor does a rung that has no message for this audience.
        return Message(to=to, rung=rung, language=lang, text="", from_template=True, guardrail=GuardrailResult(True))

    chain = as_chain(gateway)
    rejected: list[str] = []
    if chain.rungs:
        prompt = _prompt(rung, to, facts, lang, context)
        try:
            draft, used = chain.complete(SYSTEM, prompt)
            draft = draft.strip().strip('"').strip()
            g = check(draft, rung=rung, to=to, facts=facts, context=context)
            if g.passed:
                return Message(to=to, rung=rung, language=lang, text=draft, from_template=False, guardrail=g, model=used)
            rejected = g.reasons
        except ModelError:
            pass

    g = check(template, rung=rung, to=to, facts=facts, context=context)
    # The template is the floor. If it ever fails (a test should catch that first), send it anyway
    # and report why: a red flag must never go silent because a check failed.
    g = GuardrailResult(passed=g.passed, reasons=[f"draft:{r}" for r in rejected] + g.reasons)
    return Message(to=to, rung=rung, language=lang, text=template, from_template=True, guardrail=g)


def _prompt(rung: Rung, to: Audience, facts: Facts, lang: Lang, context: dict) -> str:
    said = {
        "symptoms": [s.words or s.code for s in facts.symptoms],
        "bp": [f"{b.systolic}/{b.diastolic}" for b in facts.bp],
        "doses": [{"taken": d.taken, "medicine": d.medicine} for d in facts.doses],
        "running_out": facts.running_out,
        "mood": facts.mood,
        "what_they_said_in_english": facts.english,
    }
    return "\n".join([
        f"Rung: {rung} - {RUNG_MEANING[rung]}",
        f"Write to: {to}" + (" (the senior themself)" if to == "senior" else ""),
        f"Language: {LANG_NAME[lang]}",
        f"Facts: {json.dumps(said, ensure_ascii=False)}",
        f"Context: {json.dumps(context, ensure_ascii=False, default=str)}",
    ])
