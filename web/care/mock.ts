// In-browser mock of GET /care/family/{contact}, in the contract's shapes. Synthetic data, mirroring the
// API's demo seed (Mr Tan; Wei Ling and Kelvin). Scenarios: ?scenario=quiet | handover (default) | redflag
// Claims persist in localStorage so a second tab as another family member sees who claimed.
import type { Contact, FamilyView, Handover, Message, PairCodeIn, PairCodeOut } from '../shared/contract';

const family: Contact[] = [
  { id: 'tan-weiling', senior_id: 'tan', role: 'family', primary: true, name: 'Wei Ling', language: 'en', worker_id: null },
  { id: 'tan-kelvin', senior_id: 'tan', role: 'family', primary: true, name: 'Kelvin', language: 'en', worker_id: null },
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

export function createPairCode(_body: PairCodeIn): Promise<PairCodeOut> {
  const n = Math.floor(Math.random() * 1e6);
  return delay({ code: String(n).padStart(6, '0'), senior_id: `sen-${n}`, contact_id: `con-${n}` });
}
