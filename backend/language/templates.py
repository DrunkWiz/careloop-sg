"""Fixed messages per rung, audience and language. The fallback when the model is down or its
draft fails the guardrail. Every template must pass the guardrail itself (tested).

PLACEHOLDER: the red-flag wording (rung R) is unreviewed until the medical student signs off
(Thu). Do not change its meaning without that review.

Singlish speakers get the English templates: plain English reads fine to them, and a template
that tries to sound Singlish reads as mockery.
"""
from __future__ import annotations

from collections import defaultdict

from .facts import Audience, Facts, Lang, Rung

T: dict[tuple[str, str, str], str] = {
    # 1 ask
    ("1", "senior", "en"): "Good morning{name_sep}{name}. How are you feeling today? When you have a moment, could you check your blood pressure?",
    ("1", "senior", "zh"): "{name}早上好。今天身体怎么样？方便的时候，可以量一下血压吗？",
    # 2 suggest
    ("2", "senior", "en"): "There is something you might enjoy today: {place}. Would you like to go?",
    ("2", "senior", "zh"): "今天有个活动您可能会喜欢：{place}。想去看看吗？",
    ("2", "senior:noplace", "en"): "How about calling a friend or doing something you enjoy today?",
    ("2", "senior:noplace", "zh"): "今天要不要打个电话给朋友，或者做点您喜欢的事？",
    # 3 note in digest
    ("3", "family", "en"): "For this week's digest: {summary}",
    ("3", "family", "zh"): "本周摘要：{summary}",
    # 4 hand over
    ("4", "family", "en"): "CareLoop is handing this over to you: {summary} The evidence and next steps are in the app.",
    ("4", "family", "zh"): "CareLoop 需要您接手：{summary}证据和下一步都在应用里。",
    ("4", "senior", "en"): "I have let {contact} know how your week has been, so they can check in with you.",
    ("4", "senior", "zh"): "我已经告诉{contact}您这周的情况，他们会来关心您。",
    # R red flag (PLACEHOLDER until clinical sign-off)
    ("R", "senior:symptom", "en"): "Please call 995 now, or ask someone near you to call. You told me: \"{words}\". I am telling {contact} now.",
    ("R", "senior:symptom", "zh"): "请现在马上打995，或者请身边的人帮您打。您刚才说：“{words}”。我现在就通知{contact}。",
    ("R", "senior:bp", "en"): "This reading needs attention now. Please sit down, rest for 5 minutes and measure again. If you have chest pain, face droop, slurred speech, weakness on one side, or you feel faint, call 995 now. I am telling {contact} now.",
    ("R", "senior:bp", "zh"): "这个读数现在需要注意。请坐下，休息5分钟后再量一次。如果胸口痛、脸歪、说话不清楚、一边手脚没力，或者快晕倒，请马上打995。我现在就通知{contact}。",
    ("R", "family", "en"): "Urgent: {name} reported {summary} Please call {name} now. If you cannot reach them, ask someone nearby to check on them or call 995.",
    ("R", "family", "zh"): "紧急：{name}报告了{summary}请现在马上打电话给{name}。如果联系不上，请找附近的人去看看，或打995。",
}

DEFAULTS = {
    "en": {"name": "", "contact": "your family", "place": "an activity nearby", "summary": "", "words": ""},
    "zh": {"name": "", "contact": "您的家人", "place": "附近的活动", "summary": "", "words": ""},
}

SYMPTOM_WORDS = {
    "en": {
        "chest_pain": "chest pain", "face_droop": "face drooping", "slurred_speech": "slurred speech",
        "one_sided_weakness": "weakness on one side", "fainting": "fainting", "headache": "headache",
        "dizziness": "dizziness", "breathless": "breathlessness", "palpitations": "a racing heart",
        "swelling": "swelling", "tired": "tiredness", "unwell": "feeling unwell",
    },
    "zh": {
        "chest_pain": "胸口痛", "face_droop": "脸歪", "slurred_speech": "说话不清楚", "one_sided_weakness": "一边手脚没力",
        "fainting": "晕倒", "headache": "头痛", "dizziness": "头晕", "breathless": "喘不过气", "palpitations": "心跳很快",
        "swelling": "肿", "tired": "很累", "unwell": "不舒服",
    },
}


def base_lang(lang: Lang) -> str:
    return "zh" if lang == "zh" else "en"


def summarize(facts: Facts, lang: Lang) -> str:
    """One factual sentence from the facts. Numbers appear only as the senior said them."""
    L = base_lang(lang)
    parts = []
    if facts.symptoms:
        words = [SYMPTOM_WORDS[L].get(s.code, s.code) for s in facts.symptoms]
        parts.append(("symptoms: " if L == "en" else "症状：") + ("、" if L == "zh" else ", ").join(words))
    for b in facts.bp:
        parts.append(f"BP {b.systolic}/{b.diastolic}" if L == "en" else f"血压 {b.systolic}/{b.diastolic}")
    missed = [d for d in facts.doses if not d.taken]
    if missed:
        parts.append("missed medicine" if L == "en" else "漏吃药")
    if facts.running_out:
        parts.append("medicine running out" if L == "en" else "药快吃完了")
    if not parts:
        return ""
    return ("; ".join(parts) + ".") if L == "en" else ("；".join(parts) + "。")


def render(rung: Rung, to: Audience, facts: Facts, lang: Lang, context: dict | None = None) -> str:
    if rung == "0":
        return ""
    L = base_lang(lang)
    ctx = defaultdict(str, DEFAULTS[L])
    ctx.update({k: v for k, v in (context or {}).items() if v is not None})
    ctx["name_sep"] = ", " if ctx["name"] else ""
    if not ctx["summary"]:
        ctx["summary"] = summarize(facts, lang)
    if not ctx["words"]:
        ctx["words"] = next((s.words for s in facts.symptoms if s.red_flag), "") or ctx["summary"]

    audience = "family" if to == "aac" else to
    key: tuple[str, str, str]
    if rung == "R" and audience == "senior":
        key = (rung, "senior:symptom" if facts.red_flag else "senior:bp", L)
    elif rung == "2" and audience == "senior" and not (context or {}).get("place"):
        key = (rung, "senior:noplace", L)
    else:
        key = (rung, audience, L)
    if key not in T:
        # No senior-facing digest note (rung 3): the senior is not messaged at that rung.
        return ""
    return T[key].format_map(ctx).strip()
