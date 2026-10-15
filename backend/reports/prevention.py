"""Staying well: the vaccines, screenings and check-ups a senior with high blood pressure should have,
and which of them are due. Rules, not a model.

Which items apply comes from the senior's conditions and medicines. When each was last done comes from the
care plan (`carenotes.prevention`, dates the family or centre ticks off). CareLoop doesn't store a senior's
age or sex, so items are the ones for adults 65 and over, and sex-specific screenings (mammogram, Pap test)
are left out rather than guessed.

Sources (checked 15 Oct 2026):
- Vaccines: MOH National Adult Immunisation Schedule, 1 Apr 2026 (flu every year, pneumococcal for 65+),
  and MOH's 2025/2026 COVID-19 recommendations (a yearly dose for 60+).
- Screenings: Screen for Life on HealthHub (cardiovascular risk every 3 years from 40, FIT every year from 50),
  fully subsidised at a Healthier SG clinic.
The check-up items marked PLACEHOLDER (BP review, kidney check, medicine review, diabetes eye and foot checks)
follow common primary-care practice; their intervals need the medical student's sign-off.
"""
from __future__ import annotations

from datetime import date, timedelta

from .medicines import identify

# id, applies when, every N days (None: once), placeholder, en (title, why, where), zh (title, why, where)
ITEMS = [
    ("flu", "all", 365, False,
     ("Flu vaccine", "Flu is more serious for older adults. The vaccine changes each year, so it's once a year.",
      "Polyclinic, a CHAS or Healthier SG clinic, or some pharmacies"),
     ("流感疫苗", "流感对年长者比较危险。疫苗每年更新，所以每年打一次。", "综合诊疗所、CHAS 或健康 SG 诊所，或部分药房")),
    ("pneumococcal", "all", None, False,
     ("Pneumococcal vaccine", "Protects against a common cause of pneumonia. Recommended once from 65; your doctor will say which one.",
      "Polyclinic or a CHAS or Healthier SG clinic"),
     ("肺炎球菌疫苗", "预防一种常见的肺炎病菌。65 岁起建议打；医生会说打哪一种。", "综合诊疗所、CHAS 或健康 SG 诊所")),
    ("covid", "all", 365, False,
     ("COVID-19 vaccine", "MOH recommends a yearly dose for people 60 and over. Check vaccine.gov.sg for this season's advice.",
      "Polyclinic or a vaccination clinic (free)"),
     ("冠病疫苗", "卫生部建议 60 岁以上每年打一剂。本季建议请看 vaccine.gov.sg。", "综合诊疗所或疫苗接种诊所（免费）")),
    ("bp_review", "all", 182, True,
     ("Blood pressure review", "A regular visit to check the BP medicine is still right. Bring the GP brief from CareLoop.",
      "Their own GP or polyclinic"),
     ("血压复诊", "定期看医生，确认降血压药还合适。请带上 CareLoop 的医生简报。", "自己的家庭医生或综合诊疗所")),
    ("kidney", "all", 365, True,
     ("Kidney check (blood and urine test)", "High blood pressure can affect the kidneys over time, so they are checked about once a year.",
      "At a BP review"),
     ("肾脏检查（验血和验尿）", "高血压久了可能影响肾脏，所以大约每年检查一次。", "血压复诊时")),
    ("cardio_screen", "no_diabetes", 365 * 3, False,
     ("Blood sugar and cholesterol check", "Screen for Life checks for diabetes and high cholesterol every 3 years from 40.",
      "A Healthier SG clinic (fully subsidised there)"),
     ("血糖和胆固醇检查", "Screen for Life 从 40 岁起每 3 年检查糖尿病和高胆固醇。", "健康 SG 诊所（在那里全额津贴）")),
    ("fit", "all", 365, False,
     ("Bowel cancer screening (FIT kit)", "A simple stool test done at home, once a year from 50.",
      "Collect a kit at a Healthier SG clinic, or some pharmacies and community centres"),
     ("大肠癌筛检（FIT 粪便检验）", "在家做的简单粪便检验，50 岁起每年一次。", "在健康 SG 诊所领取，或部分药房和民众俱乐部")),
    ("diabetes_eye", "diabetes", 365, True,
     ("Diabetes eye screening", "Diabetes can damage the back of the eye without any symptoms. A yearly photo of the eye catches it early.",
      "Polyclinic or a Healthier SG clinic"),
     ("糖尿病眼睛检查", "糖尿病可能在没有症状时伤害眼底。每年拍一次眼底照片可以早发现。", "综合诊疗所或健康 SG 诊所")),
    ("diabetes_foot", "diabetes", 365, True,
     ("Diabetes foot check", "Checks the feet for numbness and poor blood flow, to prevent sores.",
      "Polyclinic or a Healthier SG clinic"),
     ("糖尿病足部检查", "检查脚有没有麻木或血液循环不好，预防伤口。", "综合诊疗所或健康 SG 诊所")),
    ("med_review", "two_medicines", 365, True,
     ("Medicine review", "With two or more medicines, a pharmacist can check they still work well together.",
      "Ask the pharmacist at the polyclinic or their GP"),
     ("药物检查", "吃两种或以上的药时，药剂师可以检查它们是否还适合一起吃。", "请问综合诊疗所或家庭医生的药剂师")),
    ("healthier_sg", "all", None, False,
     ("Join Healthier SG", "A free national programme: one family doctor, a health plan, and nationally recommended screenings fully subsidised.",
      "Enrol on the HealthHub app"),
     ("加入健康 SG", "免费的全国计划：一位家庭医生、一份健康计划，国家建议的检查全额津贴。", "在 HealthHub 应用程序报名")),
]

STATUS = {
    "en": {"due": "Due", "done": "Done", "not_recorded": "Not recorded yet", "booked": "Booked"},
    "zh": {"due": "该做了", "done": "已完成", "not_recorded": "还没有记录", "booked": "已预约"},
}


def _has_diabetes(senior: dict) -> bool:
    conds = " ".join(senior.get("conditions", [])).lower()
    return "diabetes" in conds or any(identify(m.get("name", "")) == "metformin" for m in senior.get("medicines", []))


def _applies(rule: str, senior: dict) -> bool:
    if rule == "diabetes":
        return _has_diabetes(senior)
    if rule == "no_diabetes":
        return not _has_diabetes(senior)
    if rule == "two_medicines":
        return len(senior.get("medicines", [])) >= 2
    return True


def checklist(senior: dict, today: date, notes: dict | None = None, lang: str | None = None) -> dict:
    """Every item that applies, with its status. `notes` is the care plan: `prevention` holds last-done dates,
    and an upcoming appointment counts as the BP review being booked."""
    lang = lang or senior.get("language", "en")
    ui = "zh" if lang == "zh" else "en"
    done = (notes or {}).get("prevention") or {}
    upcoming = sorted(a["date"] for a in (notes or {}).get("appointments", []) if a.get("date", "") >= today.isoformat())
    items = []
    for item_id, rule, every, placeholder, en, zh in ITEMS:
        if not _applies(rule, senior):
            continue
        title, why, where = zh if ui == "zh" else en
        last = done.get(item_id)
        next_due = None
        if last:
            if every is None:
                status = "done"
            else:
                next_due = (date.fromisoformat(last) + timedelta(days=every)).isoformat()
                status = "done" if next_due > today.isoformat() else "due"
        else:
            status = "not_recorded"
        if item_id == "bp_review" and upcoming and status != "done":
            status, next_due = "booked", upcoming[0]
        items.append({
            "id": item_id, "title": title, "why": why, "where": where, "every_days": every, "last_done": last,
            "next_due": next_due, "status": status, "status_text": STATUS[ui][status], "placeholder": placeholder,
        })
    order = {"due": 0, "not_recorded": 1, "booked": 2, "done": 3}
    items.sort(key=lambda x: order[x["status"]])
    return {
        "items": items,
        "note": "For adults 65 and over with high blood pressure. Vaccines from MOH's adult immunisation schedule; screenings from Screen for Life. Check-up intervals marked as placeholders need the medical student's sign-off."
        if ui == "en" else "适合 65 岁以上、有高血压的人。疫苗参考卫生部成人免疫计划；检查参考 Screen for Life。标为占位的复诊间隔还需医学生审核。",
    }
