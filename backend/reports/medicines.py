"""What each medicine is for, in plain words, in English and Mandarin.

A fixed table, not a model: these words are shown to seniors and families as they are. They say what a
medicine is for, how it helps, and what to look out for, the kind of thing a patient leaflet says. They
never say to change, skip or stop a dose (a test holds them to the same guardrail rules as messages).
How the senior takes it comes from their own label (`dose_text`, `schedule`), never from here.

A medicine that isn't in the table is not guessed at: CareLoop says it can't identify it and points to the
pharmacist. Names match by generic name or a listed brand, never by "close enough".

PLACEHOLDER: written for the demo from standard patient-leaflet wording. The medical student or a
pharmacist must check every entry before real use.
"""
from __future__ import annotations

import re

UNKNOWN = {
    "en": "CareLoop isn't able to identify this medicine. Please check with your pharmacist what it is for.",
    "zh": "CareLoop 认不出这种药。请问您的药剂师这种药是做什么用的。",
}
ALWAYS = {
    "en": "Take it as on your label, even on days you feel well. If anything on this page worries you, ask your pharmacist or doctor.",
    "zh": "请按药袋上的说明吃药，感觉很好的日子也一样。如果这里有任何让您担心的地方，请问药剂师或医生。",
}
SCHEDULE = {
    "en": {"morning": "in the morning", "noon": "at noon", "evening": "in the evening", "night": "at night"},
    "zh": {"morning": "早上", "noon": "中午", "evening": "傍晚", "night": "晚上"},
}
GROUP_ZH = {"BP": "血压", "sugar": "血糖", "cholesterol": "胆固醇", "heart": "心脏"}

# generic name: brands, group, what it is for, how it helps, things to look out for (en, zh)
TABLE: dict[str, dict] = {
    "amlodipine": {
        "brands": ["norvasc"], "group": "BP",
        "en": ("Lowers blood pressure.", "It relaxes the blood vessels so blood flows more easily.",
               ["Swollen ankles can happen. Tell your doctor if they bother you.", "Some people feel flushed or get a headache at first."]),
        "zh": ("降血压。", "它让血管放松，血液流动更顺畅。", ["脚踝可能会肿。如果觉得不舒服，请告诉医生。", "刚开始吃时，有些人会脸红或头痛。"]),
    },
    "nifedipine": {
        "brands": ["adalat"], "group": "BP",
        "en": ("Lowers blood pressure.", "It relaxes the blood vessels so blood flows more easily.",
               ["Swollen ankles, flushing or a headache can happen. Tell your doctor if they bother you.",
                "Swallow long-acting tablets whole, as the label says."]),
        "zh": ("降血压。", "它让血管放松，血液流动更顺畅。", ["可能会脚踝肿、脸红或头痛。如果觉得不舒服，请告诉医生。", "长效药片请按说明整颗吞下。"]),
    },
    "losartan": {
        "brands": ["cozaar"], "group": "BP",
        "en": ("Lowers blood pressure, and helps protect the kidneys.", "It stops a hormone that tightens the blood vessels.",
               ["You may feel dizzy when you stand up quickly. Get up slowly.", "Your doctor may check your kidneys and potassium with a blood test."]),
        "zh": ("降血压，也帮助保护肾脏。", "它阻止一种让血管收紧的荷尔蒙。", ["站起来太快可能会头晕。请慢慢起身。", "医生可能会验血，检查肾脏和钾。"]),
    },
    "valsartan": {
        "brands": ["diovan"], "group": "BP",
        "en": ("Lowers blood pressure.", "It stops a hormone that tightens the blood vessels.",
               ["You may feel dizzy when you stand up quickly. Get up slowly.", "Your doctor may check your kidneys and potassium with a blood test."]),
        "zh": ("降血压。", "它阻止一种让血管收紧的荷尔蒙。", ["站起来太快可能会头晕。请慢慢起身。", "医生可能会验血，检查肾脏和钾。"]),
    },
    "telmisartan": {
        "brands": ["micardis"], "group": "BP",
        "en": ("Lowers blood pressure.", "It stops a hormone that tightens the blood vessels.",
               ["You may feel dizzy when you stand up quickly. Get up slowly.", "Your doctor may check your kidneys and potassium with a blood test."]),
        "zh": ("降血压。", "它阻止一种让血管收紧的荷尔蒙。", ["站起来太快可能会头晕。请慢慢起身。", "医生可能会验血，检查肾脏和钾。"]),
    },
    "lisinopril": {
        "brands": ["zestril"], "group": "BP",
        "en": ("Lowers blood pressure, and helps protect the heart and kidneys.", "It lowers a hormone that tightens the blood vessels.",
               ["A dry, tickly cough is common. Tell your doctor if you get one.", "Swelling of the lips, face or tongue is rare but urgent: call 995."]),
        "zh": ("降血压，也帮助保护心脏和肾脏。", "它减少一种让血管收紧的荷尔蒙。", ["常见干咳。如果咳嗽，请告诉医生。", "嘴唇、脸或舌头肿起来很少见，但很紧急：请打 995。"]),
    },
    "enalapril": {
        "brands": ["renitec"], "group": "BP",
        "en": ("Lowers blood pressure, and helps protect the heart and kidneys.", "It lowers a hormone that tightens the blood vessels.",
               ["A dry, tickly cough is common. Tell your doctor if you get one.", "Swelling of the lips, face or tongue is rare but urgent: call 995."]),
        "zh": ("降血压，也帮助保护心脏和肾脏。", "它减少一种让血管收紧的荷尔蒙。", ["常见干咳。如果咳嗽，请告诉医生。", "嘴唇、脸或舌头肿起来很少见，但很紧急：请打 995。"]),
    },
    "perindopril": {
        "brands": ["coversyl"], "group": "BP",
        "en": ("Lowers blood pressure, and helps protect the heart and kidneys.", "It lowers a hormone that tightens the blood vessels.",
               ["A dry, tickly cough is common. Tell your doctor if you get one.", "Swelling of the lips, face or tongue is rare but urgent: call 995."]),
        "zh": ("降血压，也帮助保护心脏和肾脏。", "它减少一种让血管收紧的荷尔蒙。", ["常见干咳。如果咳嗽，请告诉医生。", "嘴唇、脸或舌头肿起来很少见，但很紧急：请打 995。"]),
    },
    "atenolol": {
        "brands": ["tenormin"], "group": "BP",
        "en": ("Lowers blood pressure and slows the heart.", "It makes the heart beat more slowly and less forcefully.",
               ["You may feel tired, or have cold hands and feet.", "Ask your doctor before coming off it: it should not end suddenly."]),
        "zh": ("降血压，让心跳变慢。", "它让心脏跳得慢一点、轻一点。", ["可能会觉得累，或手脚冰冷。", "想不吃之前请先问医生：这种药不应该突然停。"]),
    },
    "bisoprolol": {
        "brands": ["concor"], "group": "BP",
        "en": ("Lowers blood pressure and slows the heart.", "It makes the heart beat more slowly and less forcefully.",
               ["You may feel tired, or have cold hands and feet.", "Ask your doctor before coming off it: it should not end suddenly."]),
        "zh": ("降血压，让心跳变慢。", "它让心脏跳得慢一点、轻一点。", ["可能会觉得累，或手脚冰冷。", "想不吃之前请先问医生：这种药不应该突然停。"]),
    },
    "metoprolol": {
        "brands": ["betaloc"], "group": "BP",
        "en": ("Lowers blood pressure and slows the heart.", "It makes the heart beat more slowly and less forcefully.",
               ["You may feel tired, or have cold hands and feet.", "Ask your doctor before coming off it: it should not end suddenly."]),
        "zh": ("降血压，让心跳变慢。", "它让心脏跳得慢一点、轻一点。", ["可能会觉得累，或手脚冰冷。", "想不吃之前请先问医生：这种药不应该突然停。"]),
    },
    "hydrochlorothiazide": {
        "brands": ["hctz"], "group": "BP",
        "en": ("Lowers blood pressure. A 'water pill'.", "It helps the kidneys pass out extra salt and water.",
               ["You will pass urine more often for a few hours after taking it.", "Your doctor may check your salts (sodium, potassium) with a blood test."]),
        "zh": ("降血压。也叫“利尿药”。", "它帮助肾脏排出多余的盐和水。", ["吃药后几个小时内会比较常小便。", "医生可能会验血，检查钠和钾。"]),
    },
    "indapamide": {
        "brands": ["natrilix"], "group": "BP",
        "en": ("Lowers blood pressure. A 'water pill'.", "It helps the kidneys pass out extra salt and water.",
               ["You may pass urine more often.", "Your doctor may check your salts (sodium, potassium) with a blood test."]),
        "zh": ("降血压。也叫“利尿药”。", "它帮助肾脏排出多余的盐和水。", ["可能会比较常小便。", "医生可能会验血，检查钠和钾。"]),
    },
    "metformin": {
        "brands": ["glucophage"], "group": "sugar",
        "en": ("Lowers blood sugar in type 2 diabetes.", "It helps the body use its own insulin better.",
               ["An upset stomach is common at first. Taking it with food helps.", "Your doctor will check your kidneys with a yearly blood test."]),
        "zh": ("降低二型糖尿病的血糖。", "它帮助身体更好地使用自己的胰岛素。", ["刚开始常会肠胃不舒服。和食物一起吃会好一些。", "医生每年会验血检查肾脏。"]),
    },
    "atorvastatin": {
        "brands": ["lipitor"], "group": "cholesterol",
        "en": ("Lowers cholesterol, to protect the heart and blood vessels.", "It slows how much cholesterol the liver makes.",
               ["Tell your doctor about any new muscle pain or weakness.", "It works quietly: you won't feel it working, but it still helps."]),
        "zh": ("降低胆固醇，保护心脏和血管。", "它减少肝脏制造的胆固醇。", ["如果肌肉突然酸痛或无力，请告诉医生。", "它默默地起作用：感觉不到，但还是有帮助。"]),
    },
    "simvastatin": {
        "brands": ["zocor"], "group": "cholesterol",
        "en": ("Lowers cholesterol, to protect the heart and blood vessels.", "It slows how much cholesterol the liver makes.",
               ["Tell your doctor about any new muscle pain or weakness.", "Grapefruit can interact with it. Ask your pharmacist."]),
        "zh": ("降低胆固醇，保护心脏和血管。", "它减少肝脏制造的胆固醇。", ["如果肌肉突然酸痛或无力，请告诉医生。", "西柚可能会影响这种药。请问药剂师。"]),
    },
    "aspirin": {
        "brands": ["cardiprin", "aspirin low dose"], "group": "heart",
        "en": ("Low-dose aspirin helps stop blood clots, to protect the heart and brain.", "It makes the blood less sticky.",
               ["You may bruise more easily.", "Black stools or vomiting blood are urgent: see a doctor at once or call 995."]),
        "zh": ("小量的阿司匹林帮助防止血块，保护心脏和大脑。", "它让血液不那么容易凝结。", ["可能比较容易瘀青。", "大便发黑或吐血很紧急：请马上看医生或打 995。"]),
    },
}

_BRANDS = {b: g for g, e in TABLE.items() for b in e["brands"]}


def identify(name: str) -> str | None:
    """The generic name, if the name on the label is one CareLoop knows. Strengths and forms are ignored."""
    words = re.sub(r"[^a-z ]", " ", name.lower()).split()
    text = " ".join(w for w in words if w not in ("mg", "tablet", "tablets", "tab", "capsule", "capsules", "la", "sr", "xl", "er", "cr"))
    for generic in TABLE:
        if re.search(rf"\b{generic}\b", text):
            return generic
    for brand, generic in _BRANDS.items():
        if re.search(rf"\b{re.escape(brand)}\b", text):
            return generic
    return None


def explain(med: dict, lang: str = "en") -> dict:
    """One medicine from the senior's record, explained. `lang`: en, en-SG or zh (Singlish speakers read English)."""
    ui = "zh" if lang == "zh" else "en"
    generic = identify(med.get("name", ""))
    when = [SCHEDULE[ui].get(s, s) for s in med.get("schedule", [])]
    out = {
        "name": med.get("name", ""),
        "dose_text": med.get("dose_text", ""),
        "when": when,
        "for_bp": bool(med.get("for_bp")),
        "known": generic is not None,
        "generic": generic,
    }
    if generic is None:
        out.update(group=None, what_for=UNKNOWN[ui], how_it_helps=None, look_out_for=[])
        return out
    e = TABLE[generic]
    what, how, look = e[ui]
    group = e["group"]
    out.update(group=GROUP_ZH[group] if ui == "zh" else group, what_for=what, how_it_helps=how, look_out_for=list(look))
    return out


def explain_all(senior: dict, lang: str | None = None) -> dict:
    lang = lang or senior.get("language", "en")
    ui = "zh" if lang == "zh" else "en"
    return {
        "medicines": [explain(m, lang) for m in senior.get("medicines", [])],
        "always": ALWAYS[ui],
        "note": "Plain-language notes for the demo, from standard patient-leaflet wording. PLACEHOLDER until a pharmacist or the medical student checks them."
        if ui == "en" else "演示用的说明，参考一般药物说明书的写法。还需药剂师或医学生审核（占位内容）。",
    }
