// In-browser mock of GET /care/family/{contact}, in the contract's shapes. Synthetic data, mirroring the
// API's demo seed (Mr Tan; Wei Ling and Kelvin). Scenarios: ?scenario=quiet | handover (default) | redflag
// Claims persist in localStorage so a second tab as another family member sees who claimed.
import type { CaregiverView, CareNotes, Contact, FamilyView, Handover, LogDay, Message, PairCodeIn, PairCodeOut, PairIn, PairOut, RotaView, Rung, VentPost } from '../shared/contract';

const family: Contact[] = [
  { id: 'tan-weiling', caregiver_id: 'cg-weiling', senior_id: 'tan', role: 'family', primary: true, name: 'Wei Ling', language: 'en', worker_id: null },
  { id: 'tan-kelvin', caregiver_id: 'cg-kelvin', senior_id: 'tan', role: 'family', primary: false, name: 'Kelvin', language: 'en', worker_id: null },
];

// 14 days of synthetic BP ending 24 Oct: settled, one odd reading on 15 Oct, then a drift from 21 Oct.
const series = [
  [null, null], [131, 77], [null, null], [126, 75], [157, 96], [null, null], [126, 79],
  [127, 85], [133, 85], [139, 88], [148, 91], [149, 89], [155, 95], [156, 90],
].map(([systolic, diastolic], i) => ({
  date: new Date(Date.UTC(2026, 9, 11 + i)).toISOString().slice(0, 10),
  systolic,
  diastolic,
}));

const driftHandover: Handover = {
  id: 'ho-dec-tan-2026-10-24',
  senior_id: 'tan',
  decision_id: 'dec-tan-2026-10-24',
  opened_at: '2026-10-24T21:00:00+08:00',
  kind: 'bp_drift',
  evidence: {
    summary: '7-day average systolic 144, 15 above their own baseline of 129, and over 140 on 4 of 7 days',
    bp_series: series,
    baseline: { systolic: 129, diastolic: 78 },
    dates: ['2026-10-15', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-24'],
    tried: [
      { date: '2026-10-15', rung: '1', what: 'one odd reading 157/96 against a baseline of 128; offer to re-measure' },
      { date: '2026-10-17', rung: '2', what: 'medicine running out (unspecified); suggest collecting a refill' },
      { date: '2026-10-21', rung: '3', what: '7-day average systolic 138 against a baseline of 128; over 140 on 2 days; not persistent yet' },
      { date: '2026-10-23', rung: '3', what: '7-day average systolic 140 against a baseline of 129; over 140 on 3 days; not persistent yet' },
    ],
  },
  options: [
    { id: 'polyclinic', label: 'Book a polyclinic slot' },
    { id: 'gp_note', label: 'Draft a note to the GP' },
    { id: 'call', label: 'Call them today' },
  ],
  status: 'open',
  claimed_by: null,
  claimed_at: null,
  choice: null,
};

const redFlagHandover: Handover = {
  id: 'ho-dec-tan-2026-10-25',
  senior_id: 'tan',
  decision_id: 'dec-tan-2026-10-25',
  opened_at: '2026-10-25T09:31:00+08:00',
  kind: 'red_flag',
  evidence: {
    summary: 'BP 186/112 at or above the red-flag floor (180/120)',
    bp_series: series,
    baseline: { systolic: 129, diastolic: 78 },
    dates: ['2026-10-25'],
    tried: [],
  },
  options: [
    { id: 'call_now', label: 'Call them now' },
    { id: '995', label: 'Call 995 for them' },
  ],
  status: 'open',
  claimed_by: null,
  claimed_at: null,
  choice: null,
};

const redFlagMessage = (c: Contact): Message => ({
  id: `msg-dec-tan-2026-10-25-R-family-${c.id}`,
  senior_id: 'tan',
  decision_id: 'dec-tan-2026-10-25',
  to: 'family',
  contact_id: c.id,
  rung: 'R',
  language: 'en',
  text: 'Urgent: Mr Tan reported BP 186/112 at or above the red-flag floor (180/120). Please call Mr Tan now. If you cannot reach them, ask someone nearby to check on them or call 995.',
  from_template: true,
  guardrail: { passed: true, reasons: [] },
  model: null,
  time: '2026-10-25T09:31:00+08:00',
});

type Scenario = 'quiet' | 'handover' | 'redflag';

function scenario(): Scenario {
  const s = new URLSearchParams(window.location.search).get('scenario');
  return s === 'quiet' || s === 'redflag' ? s : 'handover';
}

// --- claim store, shared with the AAC mock -------------------------------------------------

type Claim = Pick<Handover, 'status' | 'claimed_by' | 'claimed_at' | 'choice'>;
const STORE_KEY = 'careloop-mock-claims';

function loadClaims(): Record<string, Claim> {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

function saveClaims(claims: Record<string, Claim>) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(claims));
  } catch {
    /* storage unavailable: claims last for this page only */
  }
}

let claims = loadClaims();
const registry = { handovers: [driftHandover, redFlagHandover] as Handover[], contacts: [...family] as Contact[] };

export function registerMock(handovers: Handover[], contacts: Contact[]) {
  registry.handovers.push(...handovers);
  registry.contacts.push(...contacts);
}

export function applyClaims(h: Handover): Handover {
  claims = loadClaims();
  const out = { ...h, ...(claims[h.id] ?? {}) };
  if (out.claimed_by) out.claimed_by_name = registry.contacts.find((x) => x.id === out.claimed_by)?.name ?? null;
  return out;
}

export const delay = <T,>(v: T) => new Promise<T>((r) => setTimeout(() => r(v), 150));

export function claimHandover(handoverId: string, contactId: string, choice: string): Promise<Handover> {
  const h = registry.handovers.find((x) => x.id === handoverId);
  if (!h) return Promise.reject(new Error('No such handover'));
  if (!h.options.some((o) => o.id === choice)) return Promise.reject(new Error(`${choice} is not an option`));
  claims = loadClaims();
  // First to claim owns it; a later claim returns the existing owner (as the API does).
  if (!claims[handoverId]?.claimed_by) {
    claims[handoverId] = { status: 'claimed', claimed_by: contactId, claimed_at: new Date().toISOString(), choice };
    saveClaims(claims);
  }
  return delay(applyClaims(h));
}

export function resetMockClaims() {
  claims = {};
  saveClaims({});
}

// --- family view ---------------------------------------------------------------------------

export function getFamilyView(contactId: string): Promise<FamilyView> {
  const contact = family.find((c) => c.id === contactId) ?? family[0];
  const s = scenario();
  const handovers = s === 'quiet' ? [] : s === 'handover' ? [driftHandover] : [redFlagHandover, driftHandover];
  return delay({
    contact,
    senior: { id: 'tan', name: 'Mr Tan', language: 'en-SG' },
    family_sees: 'readings',
    today: s === 'redflag' ? '2026-10-25' : s === 'handover' ? '2026-10-24' : '2026-10-13',
    status: s === 'quiet' ? 'quiet' : s === 'handover' ? 'handover' : 'red_flag',
    on_duty: contactId === 'tan-kelvin', // Kelvin is on duty in this mock week
    on_duty_name: 'Kelvin',
    digest:
      s === 'quiet'
        ? {
            week_start: '2026-10-07', week_end: '2026-10-13', headline: 'quiet', readings_days: 6,
            mean_systolic: 128.4, mean_diastolic: 79.1, baseline: { systolic: 128, diastolic: 80 },
            pills_taken_days: 7, missed_days: 0, checkin_days: 7, social_days: 3, worth_raising: [],
          }
        : {
            week_start: '2026-10-18', week_end: '2026-10-24', headline: 'needs you', readings_days: 7,
            mean_systolic: 143.9, mean_diastolic: 89, baseline: { systolic: 129, diastolic: 78 },
            pills_taken_days: 7, missed_days: 0, checkin_days: 7, social_days: 3,
            worth_raising: ['7-day average systolic 140 against a baseline of 129; over 140 on 3 days; not persistent yet'],
          },
    handovers: handovers.map(applyClaims),
    red_flags: s === 'redflag' ? family.map(redFlagMessage) : [],
    other_contacts: family.filter((c) => c.id !== contact.id).map((c) => ({ id: c.id, name: c.name })),
  });
}

export function getCaregiverView(caregiverId: string): Promise<CaregiverView> {
  const contacts = family.filter((c) => c.caregiver_id === caregiverId);
  const seniors = contacts.map((c) => ({
    contact_id: c.id, senior_id: c.senior_id, senior_name: 'Mr Tan', primary: c.primary, status: 'handover' as const,
    on_duty: c.id === 'tan-kelvin',
  }));
  return delay({
    caregiver: { id: caregiverId, name: contacts[0]?.name ?? 'Unknown', language: 'en' as const, role: 'family' as const, worker_id: null },
    seniors,
  });
}

export function setPrimary(contactId: string): Promise<Contact> {
  for (const c of family) {
    c.primary = c.id === contactId;
  }
  const c = family.find((x) => x.id === contactId) ?? family[0];
  return delay({ ...c });
}

export function pair(body: PairIn): Promise<PairOut> {
  const n = Math.floor(Math.random() * 1e6);
  return delay({ senior_id: body.senior_id ?? `sen-${n}`, contact_name: 'New Contact', contact_id: `con-${n}` });
}

export function createPairCode(_body: PairCodeIn): Promise<PairCodeOut> {
  const n = Math.floor(Math.random() * 1e6);
  return delay({ code: String(n).padStart(6, '0'), caregiver_id: _body.caregiver_id ?? `cg-${n}`, senior_id: `sen-${n}`, contact_id: `con-${n}` });
}

// --- decision log (GET /senior/tan/log) ----------------------------------------------------

type MockDay = [string, Rung | null, string | null, string | null, string | null]; // date, rung, rule, reason, words

const TAN_DAYS: MockDay[] = [
  ['2026-10-25', 'R', 'R.bp_floor', 'BP 186/112 at or above the red-flag floor (180/120)', "I'm fine lah, BP 186/112"],
  ['2026-10-24', '4', '4.bp_drift', driftHandover.evidence.summary, 'Eat medicine already.'],
  ['2026-10-23', '3', '3.mild_drift', '7-day average systolic 140 against a baseline of 129; over 140 on 3 days; not persistent yet', 'Ok lah, today fine.'],
  ['2026-10-22', '3', '3.mild_drift', '7-day average systolic 137 against a baseline of 129; over 140 on 2 days; not persistent yet', 'Kopi with my kakis.'],
  ['2026-10-21', '3', '3.mild_drift', '7-day average systolic 138 against a baseline of 128; over 140 on 2 days; not persistent yet', 'Eat medicine already.'],
  ['2026-10-20', '0', '0.nothing', 'no action, because BP 139/88 within range for them (baseline 128); movement normal for them', 'Ok lah, today fine.'],
  ['2026-10-19', '0', '0.nothing', 'no action, because BP 133/85 within range for them (baseline 128); movement normal for them', 'Kopi with my kakis.'],
  ['2026-10-18', '0', '0.nothing', 'no action, because BP 127/85 within range for them (baseline 128); movement normal for them', 'Ok lah, today fine.'],
  ['2026-10-17', '2', '2.refill', 'medicine running out (unspecified); suggest collecting a refill', 'The small white one almost finish liao.'],
  ['2026-10-16', '0', '0.nothing', 'no action, because no BP reading today; movement normal for them', 'Stay home today lor, raining.'],
  ['2026-10-15', '1', '1.odd_reading', 'one odd reading 157/96 against a baseline of 128; offer to re-measure', 'Ok lah, today fine.'],
  ['2026-10-14', '0', '0.nothing', 'no action, because BP 126/75 within range for them (baseline 128); movement normal for them', 'Kopi with my kakis.'],
  ['2026-10-13', '0', '0.nothing', 'no action, because no BP reading today; movement normal for them', 'Ok lah, today fine.'],
  ['2026-10-12', '0', '0.nothing', 'no action, because BP 131/77 within range for them (baseline 128); movement normal for them', 'Eat medicine already.'],
  ['2026-10-11', '0', '0.nothing', 'no action, because no BP reading today; movement normal for them', 'Ok lah, today fine.'],
  ['2026-10-10', '0', '0.nothing', 'no action, because BP 129/80 within range for them (baseline 128); movement normal for them', 'Kopi with my kakis.'],
  ['2026-10-09', '0', '0.nothing', 'no action, because BP 127/79 within range for them (baseline 128); movement normal for them', 'Ok lah, today fine.'],
  ['2026-10-08', '0', '0.nothing', 'no action, because BP 130/81 within range for them (baseline 128); movement normal for them', 'Eat medicine already.'],
  ['2026-10-07', '0', '0.nothing', 'no action, because BP 126/78 within range for them (baseline 128); movement normal for them', 'Ok lah, today fine.'],
];

export function getLog(days: number): Promise<LogDay[]> {
  const s = scenario();
  const end = s === 'redflag' ? '2026-10-25' : s === 'handover' ? '2026-10-24' : '2026-10-13';
  const bp = (date: string, reason: string | null) => {
    const p = series.find((x) => x.date === date);
    if (p) return p.systolic != null && p.diastolic != null ? { systolic: p.systolic, diastolic: p.diastolic } : null;
    const m = reason?.match(/BP (\d+)\/(\d+)/);
    return m ? { systolic: +m[1], diastolic: +m[2] } : null;
  };
  return delay(
    TAN_DAYS.filter(([d]) => d <= end)
      .slice(0, days)
      .map(([date, rung, rule_id, reason, words]) => ({
        date, rung, rule_id, reason, decision_id: `dec-tan-${date}`,
        checkins: words ? [{ time: `${date}T08:30:00+08:00`, raw_text: words, language: 'en-SG' as const }] : [],
        replied: !!words,
        pills: 'taken' as const,
        social: !!words && /kopi|kakis/i.test(words),
        bp: bp(date, reason),
        psi: 45,
        rain_mm: words && /rain/i.test(words) ? 6.2 : 0,
        festival: null,
      })),
  );
}

// --- care notes (GET/PUT /senior/{id}/care-notes), kept in this browser for the offline demo ------

const NOTES_KEY = (sid: string) => `careloop-mock-notes-${sid}`;
const EMPTY_NOTES: CareNotes = {
  appointments: [], questions: [], tasks: [],
  emergency: { allergies: '', gp_name: '', gp_phone: '', home_address: '', notes: '' },
  updated_by: null, updated_at: null,
};

export function getCareNotes(seniorId: string): Promise<CareNotes> {
  try {
    const s = localStorage.getItem(NOTES_KEY(seniorId));
    if (s) return delay(JSON.parse(s));
  } catch {
    /* fall through */
  }
  return delay(structuredClone(EMPTY_NOTES));
}

export function putCareNotes(seniorId: string, notes: CareNotes): Promise<CareNotes> {
  const out = { ...notes, updated_at: new Date().toISOString() };
  try {
    localStorage.setItem(NOTES_KEY(seniorId), JSON.stringify(out));
  } catch {
    /* storage unavailable: kept for this page only */
  }
  return delay(out);
}

// --- vent space (Nathan): anonymous caregiver rant room, kept in this browser ----------------

const VENT_KEY = 'careloop-mock-vent';

function ventSeed(): VentPost[] {
  const now = Date.now();
  const ago = (h: number) => new Date(now - h * 3600000).toISOString();
  return [
    { id: 'vp-demo-042', nickname: 'Caregiver 042', text: "Third time this week Pa refused to take his pill, I'm so tired", time: ago(2), hugs: 3, hidden: false },
    { id: 'vp-demo-128', nickname: 'Caregiver 128', text: 'Anyone else feel guilty for needing a break?', time: ago(5), hugs: 7, hidden: false },
    { id: 'vp-demo-077', nickname: 'Caregiver 077', text: "Mum said I don't care about her. I do everything for her. That hurt.", time: ago(27), hugs: 5, hidden: false },
    { id: 'vp-demo-214', nickname: 'Caregiver 214', text: 'Finally got 6 hours of sleep last night. Small wins.', time: ago(53), hugs: 12, hidden: false },
    { id: 'vp-demo-091', nickname: 'Caregiver 091', text: "The doctor said her BP is improving. I was so relieved I cried.", time: ago(74), hugs: 8, hidden: false },
    { id: 'vp-demo-156', nickname: 'Caregiver 156', text: "Sometimes I wonder if I'm doing enough for him.", time: ago(126), hugs: 4, hidden: false },
  ];
}

function loadVent(): VentPost[] {
  try {
    const s = localStorage.getItem(VENT_KEY);
    if (s) return JSON.parse(s);
  } catch { /* fall through */ }
  const seed = ventSeed();
  try { localStorage.setItem(VENT_KEY, JSON.stringify(seed)); } catch { /* ignore */ }
  return seed;
}

function saveVent(posts: VentPost[]) {
  try { localStorage.setItem(VENT_KEY, JSON.stringify(posts)); } catch { /* ignore */ }
}

export function getVentFeed(): Promise<VentPost[]> {
  const cutoff = new Date(Date.now() - 7 * 86400000).toISOString();
  return delay(
    loadVent()
      .filter((p) => !p.hidden && p.time >= cutoff)
      .sort((a, b) => b.time.localeCompare(a.time))
      .slice(0, 100),
  );
}

export function postVent(nickname: string, text: string): Promise<VentPost> {
  const posts = loadVent();
  const post: VentPost = {
    id: `vp-${Date.now()}`,
    nickname: nickname.trim(),
    text: text.trim(),
    time: new Date().toISOString(),
    hugs: 0,
    hidden: false,
  };
  posts.unshift(post);
  saveVent(posts);
  return delay(post);
}

export function hugVentPost(postId: string): Promise<VentPost> {
  const posts = loadVent();
  const p = posts.find((x) => x.id === postId);
  if (!p) return Promise.reject(new Error('post not found'));
  p.hugs++;
  saveVent(posts);
  return delay({ ...p });
}

export function reportVentPost(postId: string): Promise<{ id: string; hidden: boolean }> {
  const posts = loadVent();
  const p = posts.find((x) => x.id === postId);
  if (!p) return Promise.reject(new Error('post not found'));
  p.hidden = true;
  saveVent(posts);
  return delay({ id: postId, hidden: true });
}

// --- rota (GET/PUT/POST/DELETE /senior/{sid}/rota) -----------------------------------------

const mockRota: RotaView = {
  rota: { id: 'rota-tan', senior_id: 'tan', mode: 'weekly', start_date: '2026-09-03', order: ['tan-weiling', 'tan-kelvin'], swaps: [] },
  on_duty: { id: 'tan-kelvin', name: 'Kelvin' },
};

export function getRota(_seniorId: string): Promise<RotaView> {
  return delay(structuredClone(mockRota));
}

export function putRota(seniorId: string, mode: 'weekly' | 'daily', startDate: string, order: string[]): Promise<RotaView> {
  mockRota.rota = { id: `rota-${seniorId}`, senior_id: seniorId, mode, start_date: startDate, order, swaps: [] };
  return delay(structuredClone(mockRota));
}

export function swapRota(seniorId: string, date: string, contactId: string): Promise<RotaView> {
  const swaps = (mockRota.rota?.swaps ?? []).filter((s) => s.date !== date);
  swaps.push({ date, contact_id: contactId });
  if (mockRota.rota) mockRota.rota.swaps = swaps;
  return delay(structuredClone(mockRota));
}

export function deleteRota(_seniorId: string): Promise<RotaView> {
  mockRota.rota = null;
  mockRota.on_duty = null;
  return delay(structuredClone(mockRota));
}

// Mr Tan's phone: Fitbit and an OMRON cuff through Health Connect. Synthetic, read-only in the mocks.
export function getHealthSync(seniorId: string, days = 7): Promise<import('../shared/contract').HealthSyncView> {
  if (seniorId !== 'tan') return delay({ connected: false, status: null, days: [], shares_readings: true, shares_activity: true });
  const today = new Date('2026-10-24T22:30:00+08:00');
  const rows = Array.from({ length: days }, (_, i) => {
    const d = new Date(today.getTime() - (days - 1 - i) * 86400000).toISOString().slice(0, 10);
    return { date: d, steps: [5480, 4930, 5650, 6010, 5210, 4870, 4470][i % 7], resting_hr: [67, 69, 68, 70, 66, 68, 71][i % 7],
      sleep_hours: [6.9, 6.2, 7.4, 6.6, 7.1, 5.9, 6.8][i % 7], bp: [{ time: `${d}T08:05:00+08:00`, systolic: 140 + i * 2, diastolic: 85 + i }] };
  });
  return delay({
    connected: true,
    status: { platform: 'health_connect', platform_name: 'Health Connect', apps: ['Fitbit', 'OMRON connect'], kinds: ['blood pressure', 'heart rate', 'sleep', 'steps'],
      last_sync: today.toISOString(), last_batch: { records: 19, readings: 4, skipped: 0 } },
    days: rows, shares_readings: true, shares_activity: true,
  });
}

// Mr Tan's medicine notes and staying-well list, as the API gives them (synthetic; offline mocks only).
export function getMedicines(): Promise<import('../shared/contract').MedicinesView> {
  return delay({
    medicines: [{ name: 'amlodipine', dose_text: '5 mg once a day', when: ['in the morning'], for_bp: true, known: true, generic: 'amlodipine', group: 'BP',
      what_for: 'Lowers blood pressure.', how_it_helps: 'It relaxes the blood vessels so blood flows more easily.',
      look_out_for: ['Swollen ankles can happen. Tell your doctor if they bother you.', 'Some people feel flushed or get a headache at first.'] }],
    always: 'Take it as on your label, even on days you feel well. If anything on this page worries you, ask your pharmacist or doctor.',
    note: 'Plain-language notes for the demo, from standard patient-leaflet wording. PLACEHOLDER until a pharmacist or the medical student checks them.',
  });
}

export function getPrevention(): Promise<import('../shared/contract').PreventionView> {
  const item = (id: string, title: string, why: string, where: string, status: 'due' | 'done' | 'not_recorded' | 'booked', status_text: string, last_done: string | null, next_due: string | null) =>
    ({ id, title, why, where, every_days: 365, last_done, next_due, status, status_text, placeholder: false });
  return delay({
    items: [
      item('flu', 'Flu vaccine', "Flu is more serious for older adults. The vaccine changes each year, so it's once a year.", 'Polyclinic, a CHAS or Healthier SG clinic, or some pharmacies', 'due', 'Due', '2025-10-04', '2026-10-04'),
      item('fit', 'Bowel cancer screening (FIT kit)', 'A simple stool test done at home, once a year from 50.', 'Collect a kit at a Healthier SG clinic', 'not_recorded', 'Not recorded yet', null, null),
      item('pneumococcal', 'Pneumococcal vaccine', 'Protects against a common cause of pneumonia. Recommended once from 65.', 'Polyclinic or a CHAS or Healthier SG clinic', 'done', 'Done', '2024-11-12', null),
    ],
    note: 'For adults 65 and over with high blood pressure. Vaccines from MOH\'s adult immunisation schedule; screenings from Screen for Life.',
  });
}
