"""The rule table. Rules pick the rung; the model never does.

Rules are checked top to bottom and the first match wins, so the order IS the policy:
red flags (which skip baseline and context), then an open handover (CareLoop stops nudging),
then hand over, note, suggest, ask, and finally rung 0 with its reason.
Each rule returns its id, a plain-English reason and every number it used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean

from . import baseline as base
from .config import T
from .history import Day

RF, HO, NOTE, SUG, ASK, ACT = T["red_flag"], T["hand_over"], T["note"], T["suggest"], T["ask"], T["activity"]


@dataclass
class Outcome:
    rung: str
    rule_id: str
    reason: str
    inputs: dict = field(default_factory=dict)
    kind: str | None = None  # handover kind at rung 4 / R


@dataclass
class Ctx:
    senior: dict
    today: date
    days: dict[date, Day]
    open_handover: dict | None = None
    recent_decisions: list[dict] = field(default_factory=list)  # last 14 days, oldest first

    @property
    def d(self) -> Day:
        return self.days[self.today]

    def last(self, n: int) -> list[Day]:
        return [self.days[self.today - timedelta(i)] for i in range(n - 1, -1, -1) if self.today - timedelta(i) in self.days]


def _new_bp_medicine(senior: dict, today: date) -> list[str]:
    out = []
    for m in senior.get("medicines", []):
        try:
            started = date.fromisoformat(m.get("started", ""))
        except ValueError:
            continue
        if 0 <= (today - started).days <= T["new_prescription_days"]:
            out.append(m["name"])
    return out


def concern_day(d: Day, steps_base: float | None) -> tuple[bool, str]:
    """Low movement AND low contact, unexplained. Returns (concern, why not / why)."""
    if not d.steps and d.replies == 0:
        return False, "no steps and no reply: missing data (phone likely at home), not decline"
    if steps_base is None or d.steps is None or d.steps >= ACT["low_movement_fraction"] * steps_base:
        return False, "movement normal for them"
    if d.social:
        return False, "low movement but social contact today"
    if d.psi is not None and d.psi > ACT["haze_psi_above"]:
        return False, f"low movement explained by haze (PSI {d.psi}); staying in is right"
    return True, "low movement and low contact, not explained by weather or haze"


def _rain_excused(ctx: Ctx, d: Day) -> bool:
    prev = ctx.days.get(d.date - timedelta(1))
    return any(x is not None and x.rain_mm is not None and x.rain_mm >= ACT["rain_mm"] for x in (d, prev))


def evaluate(ctx: Ctx, suppress: frozenset[str] = frozenset()) -> Outcome:
    """`suppress`: handover kinds already handed over and cooling down. They are skipped, so the
    table goes on to find any OTHER problem (a new problem must not hide behind an old one)."""
    d, senior = ctx.d, ctx.senior

    # R: red flags, regardless of baseline or context ---------------------------------------
    for s, di in d.bp_red_pairs:
        if s >= RF["systolic_at_or_above"] or di >= RF["diastolic_at_or_above"]:
            return Outcome("R", "R.bp_floor", f"BP {s}/{di} at or above the red-flag floor "
                           f"({RF['systolic_at_or_above']}/{RF['diastolic_at_or_above']})",
                           {"systolic": s, "diastolic": di}, "red_flag")
    low_sym = d.symptoms & set(RF["low_systolic_needs_symptom"])
    for s, di in d.bp_red_pairs:
        if s < RF["low_systolic_below"] and low_sym:
            return Outcome("R", "R.bp_low_symptom", f"BP {s}/{di} with {', '.join(sorted(low_sym))}",
                           {"systolic": s, "diastolic": di, "symptoms": sorted(low_sym)}, "red_flag")
    if d.red_symptoms:
        return Outcome("R", "R.symptom", f"danger symptom reported: {'; '.join(d.red_symptoms)}",
                       {"words": d.red_symptoms}, "red_flag")

    # An open handover: CareLoop stops nudging until someone picks a next step ---------------
    if ctx.open_handover:
        return Outcome("0", "0.handover_open", f"no action, because a handover is open since "
                       f"{ctx.open_handover['opened_at'][:10]} and waiting for the family to pick a next step",
                       {"handover_id": ctx.open_handover["id"]})

    bpb = base.bp(ctx.days, ctx.today)
    stb = base.steps(ctx.days, ctx.today)
    week = ctx.last(7)
    reading_days = [x for x in week if x.sys is not None]
    week_sys = mean(x.sys for x in reading_days) if reading_days else None
    days_over = [x for x in reading_days if x.sys > HO["drift_systolic_over"]]
    new_meds = _new_bp_medicine(senior, ctx.today)

    # 4: hand over ---------------------------------------------------------------------------
    if d.double_dose and "double_dose" not in suppress:
        return Outcome("4", "4.double_dose", "reported taking a dose twice; a pharmacist or GP should advise (PLACEHOLDER: clinical review)",
                       {}, "double_dose")

    drift = (week_sys is not None and len(reading_days) >= HO["drift_min_reading_days"]
             and week_sys >= bpb["systolic"] + HO["drift_above_baseline"]
             and len(days_over) >= HO["drift_days_over"]) and "bp_drift" not in suppress
    festival_days = [x for x in days_over if x.festival]
    if drift and len(festival_days) >= HO["drift_days_over"] - 1:
        return Outcome("3", "3.festival_spike", f"BP up during {festival_days[0].festival}; noting it, not handing over unless it persists",
                       {"week_mean_systolic": round(week_sys, 1), "baseline_systolic": bpb["systolic"], "festival_days": len(festival_days)})
    if drift and new_meds:
        return Outcome("3", "3.new_prescription", f"BP changing after a new prescription ({', '.join(new_meds)}); noting it for the GP",
                       {"week_mean_systolic": round(week_sys, 1), "baseline_systolic": bpb["systolic"], "new_medicines": new_meds})
    if drift:
        return Outcome("4", "4.bp_drift", f"7-day average systolic {week_sys:.0f}, {week_sys - bpb['systolic']:.0f} above their own "
                       f"baseline of {bpb['systolic']:.0f}, and over {HO['drift_systolic_over']} on {len(days_over)} of {len(reading_days)} days",
                       {"week_mean_systolic": round(week_sys, 1), "baseline": bpb, "days_over": len(days_over), "reading_days": len(reading_days)},
                       "bp_drift")

    missed_days = [x for x in ctx.last(HO["missed_window_days"]) if x.missed]
    if len(missed_days) >= HO["missed_bp_medicine_days"] and "missed_medicine" not in suppress:
        return Outcome("4", "4.missed_medicine", f"BP medicine missed on {len(missed_days)} of the last {HO['missed_window_days']} days",
                       {"missed_dates": [x.date.isoformat() for x in missed_days]}, "missed_medicine")

    unwell_run = ctx.last(HO["unwell_consecutive_days"])
    if len(unwell_run) == HO["unwell_consecutive_days"] and all(x.unwell for x in unwell_run) and "unwell" not in suppress:
        return Outcome("4", "4.unwell", f"feeling unwell {HO['unwell_consecutive_days']} days running",
                       {"symptoms": sorted(set().union(*(x.symptoms for x in unwell_run)))}, "unwell")

    concern = [concern_day(x, stb)[0] and not _rain_excused(ctx, x) for x in ctx.last(14)]
    this_week, last_week = sum(concern[-7:]), sum(concern[:-7])
    if this_week >= ACT["concern_days_per_week"] and last_week >= ACT["concern_days_per_week"] and "activity" not in suppress:
        return Outcome("4", "4.activity", f"low movement and low contact on {this_week} days this week and {last_week} last week",
                       {"concern_days_this_week": this_week, "concern_days_last_week": last_week, "steps_baseline": stb}, "activity")

    silent = ctx.last(HO["no_contact_days"])
    no_contact = len(silent) == HO["no_contact_days"] and all(x.replies == 0 and not x.steps for x in silent)
    weather = any(_rain_excused(ctx, x) or (x.psi or 0) > ACT["haze_psi_above"] for x in silent)
    if no_contact and not weather and senior.get("path") == "aac" and "no_contact" not in suppress:
        return Outcome("4", "4.no_contact", f"no reply and no steps for {HO['no_contact_days']} days, no weather excuse; lives alone",
                       {"days": HO["no_contact_days"]}, "no_contact")

    # 3: note in the digest ----------------------------------------------------------------
    if no_contact:
        return Outcome("3", "3.no_data", f"no reply and no steps for {HO['no_contact_days']} days" + (" (weather)" if weather else ""),
                       {"days": HO["no_contact_days"]})
    if (d.psi or 0) > T["haze"]["family_told_psi_above"]:
        return Outcome("3", "3.haze_hazardous", f"PSI {d.psi}: hazardous; family or AAC is told", {"psi": d.psi})
    if d.questions:
        return Outcome("3", "3.medicine_question", "asked whether to skip or change a medicine; noted for the GP, CareLoop does not answer",
                       {"questions": d.questions})
    mild = (week_sys is not None and len(reading_days) >= 3 and
            week_sys >= bpb["systolic"] + NOTE["mild_drift_above_baseline"] and len(days_over) >= NOTE["mild_days_over"])
    if mild:
        return Outcome("3", "3.mild_drift", f"7-day average systolic {week_sys:.0f} against a baseline of {bpb['systolic']:.0f}; "
                       f"over {HO['drift_systolic_over']} on {len(days_over)} days; not persistent yet",
                       {"week_mean_systolic": round(week_sys, 1), "baseline": bpb, "days_over": len(days_over)})
    if this_week >= ACT["concern_days_per_week"]:
        return Outcome("3", "3.activity_week", f"low movement and low contact on {this_week} days this week",
                       {"concern_days_this_week": this_week})

    # 1 (trust): a reading we can't use is asked about before anything gentler ----------------
    if d.bp_flagged or d.other_flagged:
        flags = sorted({f for r in d.bp_flagged + d.other_flagged for f in (r.get("trust") or {}).get("flags", [])})
        return Outcome("1", "1.check_reading", f"a reading failed the trust check ({', '.join(flags)}); ask to re-measure or confirm",
                       {"flags": flags})

    # 2: suggest --------------------------------------------------------------------------
    if d.running_out:
        return Outcome("2", "2.refill", f"medicine running out ({', '.join(d.running_out)}); suggest collecting a refill",
                       {"medicines": d.running_out})
    window = ctx.last(SUG["missed_pattern_days"])
    by_weekday: dict[int, int] = {}
    for x in window:
        if x.missed:
            by_weekday[x.date.weekday()] = by_weekday.get(x.date.weekday(), 0) + 1
    clustered = sorted(w for w, n in by_weekday.items() if n >= SUG["missed_same_weekday"])
    if clustered and d.missed:
        names = [("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[w] for w in clustered]
        return Outcome("2", "2.missed_pattern", f"missed doses cluster on {', '.join(names)}; offer one small habit change",
                       {"weekdays": names})
    concern_today, why = concern_day(d, stb)
    if concern_today and not _rain_excused(ctx, d):
        return Outcome("2", "2.low_day", "a low day: offer up to three nearby options they enjoy", {"steps": d.steps, "steps_baseline": stb})

    # 1: ask ------------------------------------------------------------------------------
    if d.unwell:
        return Outcome("1", "1.unwell", f"feeling unwell ({', '.join(sorted(d.symptoms))}); weather never excuses this",
                       {"symptoms": sorted(d.symptoms)})
    odd = [(s, di) for s, di in d.bp if s >= bpb["systolic"] + ASK["odd_reading_above_baseline"] or s >= ASK["odd_reading_systolic"]]
    if odd:
        return Outcome("1", "1.odd_reading", f"one odd reading {odd[0][0]}/{odd[0][1]} against a baseline of {bpb['systolic']:.0f}; offer to re-measure",
                       {"reading": list(odd[0]), "baseline": bpb})
    if d.missed:
        return Outcome("1", "1.missed_dose", "missed a dose today; ask gently", {})

    # 0: nothing, with the reason --------------------------------------------------------
    reasons = []
    if d.sys is not None:
        near = d.sys < bpb["systolic"] + NOTE["mild_drift_above_baseline"]
        reasons.append(f"BP {d.sys:.0f}/{d.dia:.0f} " + (f"within range for them (baseline {bpb['systolic']:.0f})" if near
                       else f"above their baseline of {bpb['systolic']:.0f}, but one day is not a pattern"))
    if _rain_excused(ctx, d) and d.steps is not None and stb and d.steps < ACT["low_movement_fraction"] * stb:
        reasons.append("low movement explained by rain")
    else:
        reasons.append(why)
    if d.festival:
        reasons.append(f"{d.festival} week")
    return Outcome("0", "0.nothing", "no action, because " + "; ".join(reasons), {"baseline": bpb, "steps": d.steps, "steps_baseline": stb})
