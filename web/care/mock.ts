// Synthetic demo data for the family view, shaped like GET /care/family/{contact}.
// Scenarios: ?scenario=quiet | drift (default) | redflag
// Claims persist in localStorage so a second tab as another family member sees who claimed.
import type { Contact, FamilyView, Handover, Senior } from '../shared/contract';

const senior: Senior = {
  id: 's-tan',
  name: 'Tan Ah Kow',
  language: 'en',
  home_postal_code: '560123',
  region: 'central',
  conditions: ['hypertension'],
  medicines: [{ name: 'Amlodipine', dose: '5 mg', times: ['08:00'] }],
  likes: ['mahjong', 'morning market', 'karaoke'],
  consent: { family_sees: 'readings' },
};

const family: Contact[] = [
  { id: 'c-meiling', senior_id: 's-tan', role: 'family', primary: true, name: 'Mei Ling' },
  { id: 'c-weijie', senior_id: 's-tan', role: 'family', primary: true, name: 'Wei Jie' },
];

const baseline = { systolic: 132, diastolic: 82 };

// 14 days of synthetic BP: settled for a week, then a drift from 7 Oct.
const series = [
  [131, 81], [134, 83], [129, 80], [133, 82], [130, 81], [135, 84], [132, 82],
  [141, 87], [144, 88], [139, 86], [146, 90], [148, 91], [143, 88], [147, 90],
].map(([systolic, diastolic], i) => {
  const d = new Date(Date.UTC(2026, 8, 30 + i));
  return { date: d.toISOString().slice(0, 10), systolic, diastolic };
});

const driftHandover: Handover = {
  id: 'h-drift-1',
  senior_id: 's-tan',
  kind: 'drift',
  opened_at: '2026-10-13T09:40:00+08:00',
  evidence: {
    summary:
      "Dad's blood pressure has been higher than his usual for 7 days. His 7-day average is 144/89, against his usual 132/82, and it was over 140 on 6 of the last 7 days.",
    since: '2026-10-07',
    tried: [
      { date: '2026-10-07', rung: 1, what: 'Asked him to measure again after resting. Second reading was similar.' },
      { date: '2026-10-09', rung: 2, what: 'Suggested taking his pill at breakfast, as two doses were late. He agreed.' },
      { date: '2026-10-11', rung: 3, what: 'Noted the rise in your weekly digest.' },
    ],
    bp_series: series,
    baseline,
  },
  options: [
    { id: 'polyclinic', label: 'Book a polyclinic appointment' },
    { id: 'gp_note', label: 'Draft a note to his GP' },
    { id: 'call', label: 'Call Dad today' },
  ],
  claimed_by: null,
  claimed_by_name: null,
  claimed_at: null,
  chosen_option: null,
};

const redFlagHandover: Handover = {
  id: 'h-red-1',
  senior_id: 's-tan',
  kind: 'red_flag',
  opened_at: '2026-10-13T09:32:00+08:00',
  evidence: {
    summary: 'Dad logged a blood pressure of 186/112. CareLoop told him to call 995 or see a doctor now.',
    since: '2026-10-13',
    tried: [],
    reported: {
      time: '2026-10-13T09:31:00+08:00',
      words: "I'm fine lah",
      reading: { systolic: 186, diastolic: 112 },
    },
  },
  options: [
    { id: 'call', label: 'Call Dad now' },
    { id: 'call_995', label: 'Call 995 for him' },
  ],
  claimed_by: null,
  claimed_by_name: null,
  claimed_at: null,
  chosen_option: null,
};

type Scenario = 'quiet' | 'drift' | 'redflag';

function scenario(): Scenario {
  const s = new URLSearchParams(window.location.search).get('scenario');
  return s === 'quiet' || s === 'redflag' ? s : 'drift';
}

const STORE_KEY = 'careloop-mock-claims';

function loadClaims(): Record<string, Pick<Handover, 'claimed_by' | 'claimed_by_name' | 'claimed_at' | 'chosen_option'>> {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

function saveClaims(claims: ReturnType<typeof loadClaims>) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(claims));
  } catch {
    /* storage unavailable: claims last for this page only */
  }
}

let sessionClaims = loadClaims();

function withClaim(h: Handover): Handover {
  return { ...h, ...(sessionClaims[h.id] ?? {}) };
}

export const delay = <T,>(v: T) => new Promise<T>((r) => setTimeout(() => r(v), 150));

export function getFamilyView(contactId: string): Promise<FamilyView> {
  sessionClaims = loadClaims();
  const contact = family.find((c) => c.id === contactId) ?? family[0];
  const s = scenario();

  const handovers = s === 'drift' ? [driftHandover] : s === 'redflag' ? [redFlagHandover] : [];

  const status =
    s === 'quiet'
      ? { week_line: 'A quiet week. Dad took his pills every day and his readings were his usual.', rung_today: 0 as const }
      : s === 'drift'
        ? { week_line: "Dad's blood pressure has been above his usual this week. CareLoop needs you to pick a next step.", rung_today: 4 as const }
        : { week_line: 'Dad reported a dangerous blood pressure reading this morning.', rung_today: 'R' as const };

  return delay({
    contact,
    senior,
    family,
    status: { ...status, as_of: '2026-10-13' },
    digest: {
      week_of: '2026-10-05',
      lines:
        s === 'quiet'
          ? [
              'Dad had a steady week and checked in every morning.',
              'He took his amlodipine on all 7 days.',
              'He played mahjong on Tuesday and Saturday.',
              'Nothing to raise at his next visit.',
            ]
          : [
              'Dad checked in every morning this week.',
              'He took his amlodipine on 5 of 7 days; two doses were late.',
              'His blood pressure was higher than his usual from Wednesday.',
              'Worth raising at his next visit: the rise since 7 Oct, and whether the pill timing matters.',
            ],
    },
    handovers: handovers.map(withClaim),
    synthetic: true,
  });
}

// Handovers and contacts from every mock (family + AAC), so one claim store serves both views.
const registry = { handovers: [driftHandover, redFlagHandover] as Handover[], contacts: [...family] as Contact[] };

export function registerMock(handovers: Handover[], contacts: Contact[]) {
  registry.handovers.push(...handovers);
  registry.contacts.push(...contacts);
}

export function applyClaims(hs: Handover[]): Handover[] {
  sessionClaims = loadClaims();
  return hs.map(withClaim);
}

export function claimHandover(handoverId: string, contactId: string, optionId: string): Promise<Handover> {
  const h = registry.handovers.find((x) => x.id === handoverId);
  if (!h) return Promise.reject(new Error('No such handover'));
  sessionClaims = loadClaims();
  // First to claim owns it; a later claim returns the existing owner.
  if (!sessionClaims[handoverId]?.claimed_by) {
    const who = registry.contacts.find((c) => c.id === contactId);
    sessionClaims[handoverId] = {
      claimed_by: contactId,
      claimed_by_name: who?.name ?? 'Someone',
      claimed_at: new Date().toISOString(),
      chosen_option: optionId,
    };
    saveClaims(sessionClaims);
  }
  return delay(withClaim(h));
}

export function resetMockClaims() {
  sessionClaims = {};
  saveClaims({});
}
