// Plain words for what the engine decided. Fixed text per rule id, no model: the engine's own reason is
// still shown underneath wherever the person may see it. Rule ids come from backend/engine/rules.py.
import type { Handover, LogDay, Rung } from '../shared/contract';

export type Tone = 'quiet' | 'nudge' | 'note' | 'handover' | 'red' | 'none';

export function toneOf(rung: Rung | null): Tone {
  if (rung == null) return 'none';
  if (rung === 'R') return 'red';
  if (rung === '4') return 'handover';
  if (rung === '3') return 'note';
  if (rung === '1' || rung === '2') return 'nudge';
  return 'quiet';
}

export const TONE_LABEL: Record<Tone, string> = {
  quiet: 'Nothing needed',
  nudge: 'A gentle nudge',
  note: 'Noted',
  handover: 'Handed to you',
  red: 'Red flag',
  none: 'No decision',
};

const RULES: Record<string, string> = {
  '0.nothing': 'Nothing needed. Readings and routine were normal for them.',
  '0.handover_open': 'Waiting. A handover is already open, so CareLoop held back.',
  '0.aac_weekly_cap': 'Noted quietly. The centre gets at most one non-urgent alert a week.',
  '1.check_reading': 'A reading looked wrong. CareLoop asked them to measure again.',
  '1.missed_dose': 'Missed a dose. CareLoop asked gently.',
  '1.odd_reading': 'One unusual reading. CareLoop offered to re-measure.',
  '1.unwell': 'Said they felt unwell. CareLoop asked how they are.',
  '2.low_day': 'A quieter day. CareLoop suggested something nearby they enjoy.',
  '2.missed_pattern': 'Missed doses on the same days each week. CareLoop suggested one small habit change.',
  '2.refill': 'Medicine running low. CareLoop reminded them to collect a refill.',
  '3.activity_week': 'Less active and less in touch this week. Noted.',
  '3.already_handed_over': 'Still above usual. Already handed over to you.',
  '3.festival_spike': 'Blood pressure up over the festive days. Watching, not alarming.',
  '3.haze_hazardous': 'Hazardous haze. CareLoop advised staying indoors.',
  '3.medicine_question': 'Asked about changing a medicine. Saved for the doctor; CareLoop does not answer that.',
  '3.mild_drift': 'Blood pressure a little above their usual. Watching for a few more days.',
  '3.new_prescription': 'Blood pressure changing after a new medicine. Noted for the doctor.',
  '3.no_data': 'No reply or steps for a few days. Noted.',
  '4.bp_drift': 'Blood pressure stayed above their usual. Handed to you to decide.',
  '4.double_dose': 'May have taken a dose twice. Handed to you to check with a pharmacist or GP.',
  '4.missed_medicine': 'Blood pressure medicine missed on several days. Handed to you.',
  '4.unwell': 'Unwell several days running. Handed to you.',
  '4.activity': 'Less active and less in touch for two weeks. Handed to you.',
  '4.no_contact': 'No reply for days, with no weather to explain it. Handed to you.',
  'R.bp': 'A dangerous blood pressure reading. Everyone was told at once.',
  'R.bp_floor': 'A dangerous blood pressure reading. Everyone was told at once.',
  'R.bp_low_symptom': 'Low blood pressure with dizziness or fainting. Everyone was told at once.',
  'R.symptom': 'A danger symptom was reported. Everyone was told at once.',
};

export function ruleText(ruleId: string | null, rung: Rung | null): string {
  if (ruleId && RULES[ruleId]) return RULES[ruleId];
  if (rung == null) return 'Not shared, or no data yet that day.';
  return TONE_LABEL[toneOf(rung)] + '.';
}

const avg = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

// One sentence a family member can read at a glance. Numbers come straight from the evidence.
export function plainSummary(h: Handover, name: string): string {
  const e = h.evidence;
  const last7 = e.bp_series.slice(-7).filter((p) => p.systolic != null && p.diastolic != null);
  switch (h.kind) {
    case 'bp_drift':
      if (last7.length && e.baseline) {
        const s = Math.round(avg(last7.map((p) => p.systolic!)));
        const d = Math.round(avg(last7.map((p) => p.diastolic!)));
        const over = last7.filter((p) => p.systolic! > 140).length;
        return `${name}'s blood pressure has stayed above their usual. This week it averaged ${s}/${d}, against their usual ${Math.round(e.baseline.systolic)}/${Math.round(e.baseline.diastolic)}, and was over 140 on ${over} of ${last7.length} readings.`;
      }
      return `${name}'s blood pressure has stayed above their usual for several days.`;
    case 'missed_medicine':
      return `${name} has missed their blood pressure medicine on several days.`;
    case 'unwell':
      return `${name} has said they feel unwell several days running.`;
    case 'activity':
      return `${name} has been less active and less in touch for two weeks.`;
    case 'no_contact':
      return `${name} hasn't replied for several days, and there was no rain or haze to explain it.`;
    case 'double_dose':
      return `${name} may have taken a dose twice.`;
    case 'red_flag':
      return `${name} reported something dangerous. ${cap(e.summary)}.`;
  }
}

export function contextNotes(d: LogDay): string[] {
  const notes: string[] = [];
  if (d.rain_mm && d.rain_mm >= 1) notes.push(`Rain (${d.rain_mm} mm)`);
  if (d.psi && d.psi > 100) notes.push(`Haze (PSI ${d.psi})`);
  if (d.festival) notes.push(d.festival);
  if (d.social) notes.push('Saw friends or family');
  return notes;
}

export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
