// In-browser mock of the AAC endpoints, in the contract's shapes. Synthetic people only.
// Worker "aac-siti" (as in the API's demo seed) with Mdm Lee, Mr Goh and Mr Ng from the seed, plus two more
// so the caseload shows a handover and a no-contact case. ?scenario=redflag adds a red flag for Mdm Lee.
import type {
  BriefData,
  Caseload,
  CaseloadRow,
  Contact,
  Handover,
  LogDay,
  Programme,
  ProgrammeIn,
  Rung,
  SeniorRef,
} from '../shared/contract';
import { applyClaims, delay, registerMock } from './mock';

const WORKER = 'aac-siti';
const AAC = { id: 'aac-105', name: 'Sample AAC (Bedok North)' };
const TODAY = '2026-10-24';

const S: Record<string, SeniorRef> = {
  ong: { id: 'ong', name: 'Mr Ong', language: 'zh' },
  aminah: { id: 'aminah', name: 'Mdm Aminah', language: 'en' },
  lee: { id: 'lee', name: 'Mdm Lee', language: 'en' },
  goh: { id: 'goh', name: 'Mr Goh', language: 'zh' },
  ng: { id: 'ng', name: 'Mr Ng', language: 'en-SG' },
};

const contacts: Contact[] = Object.values(S).map((s) => ({
  id: `${WORKER}:${s.id}`, senior_id: s.id, role: 'aac', primary: true, name: 'Siti (AAC)', language: 'en', worker_id: WORKER,
}));

const day = (offset: number) => new Date(Date.UTC(2026, 9, 24 - offset)).toISOString().slice(0, 10);

const ongSeries = [
  [128, 79], [131, 80], [127, 78], [null, null], [129, 79], [132, 81], [130, 80],
  [141, 86], [143, 87], [141, 86], [145, 89], [147, 90], [144, 88], [146, 89],
].map(([systolic, diastolic], i) => ({ date: day(13 - i), systolic, diastolic }));

const ongHandover: Handover = {
  id: 'ho-dec-ong-2026-10-24',
  senior_id: 'ong',
  decision_id: 'dec-ong-2026-10-24',
  opened_at: '2026-10-24T09:50:00+08:00',
  kind: 'bp_drift',
  evidence: {
    summary: '7-day average systolic 144, 14 above their own baseline of 130, and over 140 on 7 of 7 days',
    bp_series: ongSeries,
    baseline: { systolic: 130, diastolic: 80 },
    dates: ongSeries.slice(7).map((p) => p.date),
    tried: [
      { date: '2026-10-18', rung: '1', what: 'one odd reading 141/86 against a baseline of 130; offer to re-measure' },
      { date: '2026-10-21', rung: '3', what: '7-day average systolic 136 against a baseline of 130; over 140 on 4 days; not persistent yet' },
    ],
  },
  options: [
    { id: 'call', label: 'Call them today' },
    { id: 'home_visit', label: 'Home visit this week' },
    { id: 'gp_note', label: 'Draft a note to the GP' },
  ],
  status: 'open',
  claimed_by: null,
  claimed_at: null,
  choice: null,
};

const aminahHandover: Handover = {
  id: 'ho-dec-aminah-2026-10-24',
  senior_id: 'aminah',
  decision_id: 'dec-aminah-2026-10-24',
  opened_at: '2026-10-24T12:00:00+08:00',
  kind: 'no_contact',
  evidence: {
    summary: 'no reply to check-ins for 3 days and very low movement, not explained by rain or haze',
    bp_series: [],
    baseline: null,
    dates: [day(2), day(1), day(0)],
    tried: [
      { date: day(1), rung: '3', what: 'no reply and no steps for 2 days' },
    ],
  },
  options: [
    { id: 'call', label: 'Call them today' },
    { id: 'home_visit', label: 'Home visit today' },
  ],
  status: 'open',
  claimed_by: null,
  claimed_at: null,
  choice: null,
};

const leeRedFlag: Handover = {
  id: 'ho-dec-lee-2026-10-24',
  senior_id: 'lee',
  decision_id: 'dec-lee-2026-10-24',
  opened_at: '2026-10-24T09:18:00+08:00',
  kind: 'red_flag',
  evidence: { summary: 'a danger symptom: chest pain', bp_series: [], baseline: null, dates: [TODAY], tried: [] },
  options: [
    { id: 'call_now', label: 'Call them now' },
    { id: '995', label: 'Call 995 for them' },
  ],
  status: 'open',
  claimed_by: null,
  claimed_at: null,
  choice: null,
};

registerMock([ongHandover, aminahHandover, leeRedFlag], contacts);

function row(s: SeniorRef, status: CaseloadRow['status'], rung: Rung, reason: string, last: string | null, h: Handover | null): CaseloadRow {
  return { senior: s, contact_id: `${WORKER}:${s.id}`, status, today: { rung, reason }, handover: h ? applyClaims(h) : null, last_reply: last };
}

export function getCaseload(_workerId: string): Promise<Caseload> {
  const red = new URLSearchParams(window.location.search).get('scenario') === 'redflag';
  const rows = [
    red
      ? row(S.lee, 'red_flag', 'R', 'a danger symptom: chest pain', '2026-10-24T09:18:00+08:00', leeRedFlag)
      : row(S.lee, 'quiet', '0', 'no action, because BP 132/87 within range for them (baseline 134); movement normal for them', '2026-10-24T09:30:00+08:00', null),
    row(S.ong, 'handover', '4', ongHandover.evidence.summary, '2026-10-24T08:55:00+08:00', ongHandover),
    row(S.aminah, 'handover', '4', aminahHandover.evidence.summary, '2026-10-21T09:30:00+08:00', aminahHandover),
    row(S.goh, 'quiet', '0', 'no action, because BP 126/82 within range for them (baseline 126); movement normal for them', '2026-10-24T09:30:00+08:00', null),
    row(S.ng, 'quiet', '3', 'low movement and low contact on 4 days this week (AAC caseload row only, no alert)', '2026-10-24T09:30:00+08:00', null),
  ];
  const order = { red_flag: 0, handover: 1, quiet: 2 };
  rows.sort((a, b) => order[a.status] - order[b.status] || a.senior.name.localeCompare(b.senior.name));
  return delay({ worker_id: WORKER, today: TODAY, seniors: rows });
}

export function getBrief(seniorId: string): Promise<BriefData> {
  return delay({
    senior: { id: seniorId, name: S[seniorId]?.name ?? seniorId, conditions: ['hypertension'], medicines: [] },
    period: { from: '2026-07-27', to: TODAY },
    aac: { ...AAC, going: [] },
  });
}

// --- befriending record (proposed endpoint) ------------------------------------------------

const quiet = (said: string, time = '09:15'): [Rung, string, string, string | null, string] =>
  ['0', '0.nothing', 'no action, because BP within range for them; movement normal for them', said, time];

const LOGS: Record<string, [Rung, string, string, string | null, string][]> = {
  aminah: [
    ['4', '4.no_contact', 'no reply to check-ins for 3 days and very low movement, not explained by rain or haze', null, ''],
    ['3', '3.no_data', 'no reply and no steps for 2 days', null, ''],
    ['0', '0.nothing', 'no action, because one day without a reply never escalates', null, ''],
    quiet('Morning! Took my medicine. Going to the market.', '09:30'),
    quiet('Ok, medicine taken.'),
    quiet('Good morning. Cooking for my neighbour today.'),
    quiet('Taken already.'),
  ],
  ong: [
    ['4', '4.bp_drift', ongHandover.evidence.summary, '早上好，药吃了', '08:55'],
    quiet('吃了'),
    quiet('吃了，去咖啡店'),
    ['3', '3.mild_drift', '7-day average systolic 136 against a baseline of 130; over 140 on 4 days; not persistent yet', '吃了', '09:10'],
    quiet('好'),
    quiet('昨天吃了很多卤面'),
    ['1', '1.odd_reading', 'one odd reading 141/86 against a baseline of 130; offer to re-measure', '早', '09:01'],
  ],
  ng: [
    ['3', '3.activity_week', 'low movement and low contact on 4 days this week (AAC caseload row only, no alert)', 'Stay home today lor.', '09:30'],
    ['0', '0.nothing', 'no action, because low movement explained by rain (NEA rainfall, nearest station)', 'Raining, stay home.', '09:40'],
    quiet('Eat medicine already.'),
    ['0', '0.nothing', 'no action, because one low day never escalates', 'Stay home today lor.', '09:20'],
    quiet('Kopi with my kakis.'),
    ['0', '0.nothing', 'no action, because one low day never escalates', 'Stay home today lor.', '09:25'],
    quiet('Ok lah, today fine.'),
  ],
};

export function getLog(seniorId: string, n = 7): Promise<LogDay[] | null> {
  const base = LOGS[seniorId] ?? [];
  const filler = quiet(S[seniorId]?.language === 'zh' ? '我吃了药。' : 'Took my pills.');
  const days = Array.from({ length: n }, (_, i) => base[i] ?? filler);
  const red = seniorId === 'lee' && new URLSearchParams(window.location.search).get('scenario') === 'redflag';
  return delay(
    days.map(([rung, rule_id, reason, said, time], i): LogDay => {
      if (red && i === 0) {
        [rung, rule_id, reason, said, time] = ['R', 'R.symptom', 'a danger symptom: chest pain', 'chest pain since morning', '09:18'];
      }
      const bp = reason.match(/BP (\d+)\/(\d+)/);
      return {
        date: day(i), rung, rule_id, reason, decision_id: `dec-${seniorId}-${day(i)}`,
        checkins: said ? [{ time: `${day(i)}T${time}:00+08:00`, raw_text: said, language: S[seniorId]?.language ?? 'en' }] : [],
        replied: !!said,
        pills: said ? 'taken' : null,
        social: !!said && /kopi|friends|kakis|咖啡|market|neighbour/i.test(said),
        bp: bp ? { systolic: +bp[1], diastolic: +bp[2] } : null,
        psi: 45,
        rain_mm: /rain/i.test(reason) ? 8.4 : 0,
        festival: null,
      };
    }),
  );
}

// --- programmes ----------------------------------------------------------------------------

const PROG_KEY = 'careloop-mock-programmes';

const samples: Programme[] = ([
  { title: 'Morning exercise', weekdays: ['mon', 'wed', 'fri'], time: '09:00', tags: ['exercise'], indoor: false, free: true },
  { title: 'Communal lunch', weekdays: ['tue'], time: '11:30', tags: ['food', 'chatting'], indoor: true, free: false },
  { title: 'Karaoke afternoon', weekdays: ['wed'], time: '14:00', tags: ['singing'], indoor: true, free: true },
  { title: 'Health talk: knowing your blood pressure', weekdays: ['thu'], time: '10:00', tags: ['learning'], indoor: true, free: true },
  { title: 'Arts and crafts', weekdays: ['fri'], time: '15:00', tags: ['crafts'], indoor: true, free: true },
] as ProgrammeIn[]).map((p, i) => ({ ...p, id: `prog-${AAC.id}-${i}`, place_id: AAC.id, sample: true }));

export function getProgrammes(_aacId: string): Promise<Programme[]> {
  try {
    const saved = localStorage.getItem(PROG_KEY);
    if (saved) return delay(JSON.parse(saved));
  } catch {
    /* fall through to samples */
  }
  return delay(samples);
}

export function putProgrammes(aacId: string, list: ProgrammeIn[]): Promise<Programme[]> {
  const out = list.map((p, i) => ({ ...p, id: `prog-${aacId}-${i}`, place_id: aacId, sample: false }));
  try {
    localStorage.setItem(PROG_KEY, JSON.stringify(out));
  } catch {
    /* storage unavailable: kept for this page only */
  }
  return delay(out);
}
