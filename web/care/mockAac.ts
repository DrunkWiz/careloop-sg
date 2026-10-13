// Synthetic demo data for the AAC view, shaped like GET /care/aac/{contact}/caseload.
// Every senior here is fictional. Scenarios: ?scenario=redflag adds a red flag; anything else is the default.
import type { AacCaseload, CaseloadRow, Contact, Handover, LogDay, Programme, Rung, Senior } from '../shared/contract';
import { applyClaims, delay, registerMock } from './mock';

const staff: Contact[] = [
  { id: 'c-aac-farah', senior_id: '', role: 'aac', primary: true, name: 'Farah' },
  { id: 'c-aac-daniel', senior_id: '', role: 'aac', primary: true, name: 'Daniel' },
];

function senior(id: string, name: string, language: Senior['language'], likes: string[]): Senior {
  return {
    id,
    name,
    language,
    home_postal_code: '570123',
    region: 'central',
    conditions: ['hypertension'],
    medicines: [{ name: 'Amlodipine', dose: '5 mg', times: ['08:00'] }],
    likes,
    consent: { family_sees: 'readings' }, // agreed at AAC enrolment
  };
}

const S = {
  ong: senior('s-ong', 'Mr Ong Boon Hock', 'zh', ['chess', 'kopi with friends']),
  siti: senior('s-siti', 'Mdm Siti binte Rahman', 'en', ['cooking', 'gardening']),
  raj: senior('s-raj', 'Mr Raj Kumar', 'en', ['karaoke', 'walking']),
  lim: senior('s-lim', 'Mdm Lim Siew Eng', 'zh', ['qigong', 'market']),
  chua: senior('s-chua', 'Mr Chua Kim Seng', 'zh', ['newspaper', 'morning exercise']),
  wong: senior('s-wong', 'Mdm Wong Mei Fong', 'zh', ['mahjong']),
  tan: senior('s-tangh', 'Mdm Tan Gek Hoon', 'en', ['arts and crafts', 'communal lunch']),
};

// Seven days, newest first: 13 Oct back to 7 Oct.
const DAYS = Array.from({ length: 7 }, (_, i) => new Date(Date.UTC(2026, 9, 13 - i)).toISOString().slice(0, 10));

type Day = [Rung, string, string, string | null, string?]; // rung, rule id, reason, check-in words, check-in time

function log(seniorId: string, days: Day[]): LogDay[] {
  return days.map(([rung, rule_id, reason, words, time = '09:15'], i) => ({
    decision: { senior_id: seniorId, date: DAYS[i], rung, rule_id, reason, inputs_used: [] },
    checkin: words
      ? { senior_id: seniorId, time: `${DAYS[i]}T${time}:00+08:00`, raw_text: words, language: 'en', extracted_facts: {} }
      : null,
  }));
}

const quietDay = (words: string): Day => [0, 'R0-in-range', 'No action: readings in usual range, pills taken.', words];

const ongSeries = [
  [128, 79], [131, 80], [127, 78], [130, 80], [129, 79], [132, 81], [130, 80],
  [141, 86], [143, 87], [141, 86], [145, 89], [147, 90], [144, 88], [146, 89],
].map(([systolic, diastolic], i) => ({
  date: new Date(Date.UTC(2026, 8, 30 + i)).toISOString().slice(0, 10),
  systolic,
  diastolic,
}));

const ongHandover: Handover = {
  id: 'h-aac-ong',
  senior_id: S.ong.id,
  kind: 'drift',
  opened_at: '2026-10-13T09:50:00+08:00',
  evidence: {
    summary:
      "Mr Ong's blood pressure has been above his usual for 7 days. His 7-day average is 144/88, against his usual 130/80, and it was over 140 on 7 of 7 days.",
    since: '2026-10-07',
    tried: [
      { date: '2026-10-07', rung: 1, what: 'Asked him to measure again after resting. Second reading was similar.' },
      { date: '2026-10-09', rung: 2, what: 'Suggested a lower-salt option at lunch. He said he would try.' },
      { date: '2026-10-11', rung: 3, what: 'Logged a mild rise. No alert sent.' },
    ],
    bp_series: ongSeries,
    baseline: { systolic: 130, diastolic: 80 },
  },
  options: [
    { id: 'call', label: 'Call him today' },
    { id: 'home_visit', label: 'Home visit this week' },
    { id: 'gp_note', label: 'Draft a note to his GP' },
    { id: 'polyclinic', label: 'Help book a polyclinic appointment' },
  ],
  claimed_by: null,
  claimed_by_name: null,
  claimed_at: null,
  chosen_option: null,
};

const sitiHandover: Handover = {
  id: 'h-aac-siti',
  senior_id: S.siti.id,
  kind: 'no_contact',
  opened_at: '2026-10-13T12:00:00+08:00',
  evidence: {
    summary:
      'Mdm Siti has not replied to her morning check-in for 3 days, and her phone shows almost no movement. There was no rain or haze to explain it.',
    since: '2026-10-11',
    tried: [
      { date: '2026-10-11', rung: 1, what: 'Sent her check-in again at noon. No reply.' },
      { date: '2026-10-12', rung: 1, what: 'Sent a gentler check-in in the evening. No reply.' },
    ],
  },
  options: [
    { id: 'call', label: 'Call her today' },
    { id: 'home_visit', label: 'Home visit today' },
  ],
  claimed_by: null,
  claimed_by_name: null,
  claimed_at: null,
  chosen_option: null,
};

const limRedFlag: Handover = {
  id: 'h-aac-lim-red',
  senior_id: S.lim.id,
  kind: 'red_flag',
  opened_at: '2026-10-13T09:20:00+08:00',
  evidence: {
    summary: 'Mdm Lim mentioned chest pain in her check-in. CareLoop told her to call 995 or see a doctor now.',
    since: '2026-10-13',
    tried: [],
    reported: { time: '2026-10-13T09:18:00+08:00', words: '今天还好，就是胸口有点痛' },
  },
  options: [
    { id: 'call', label: 'Call her now' },
    { id: 'call_995', label: 'Call 995 for her' },
  ],
  claimed_by: null,
  claimed_by_name: null,
  claimed_at: null,
  chosen_option: null,
};

registerMock([ongHandover, sitiHandover, limRedFlag], staff);

function rows(redflag: boolean): CaseloadRow[] {
  const r: CaseloadRow[] = [
    {
      senior: S.ong,
      status: 'handover',
      line: 'BP above his usual for 7 days. Needs a next step.',
      last_checkin: '2026-10-13T08:55:00+08:00',
      handover: ongHandover,
      alert_this_week: true,
      log: log(S.ong.id, [
        [4, 'R4-drift', 'Hand over: 7-day average 14 above baseline and over 140 on 7 of 7 days.', '早上好，药吃了', '08:55'],
        [0, 'R0-wait', 'No action: rise already noted, waiting for the pattern to settle or persist.', '吃了', '09:10'],
        [3, 'R3-mild-drift', 'Note: mild rise, not yet persistent.', '吃了，去咖啡店', '09:02'],
        [0, 'R0-wait', 'No action: suggestion made yesterday, waiting.', '好', '09:00'],
        [2, 'R2-suggest', 'Suggest: lower-salt lunch option.', '昨天吃了很多卤面', '09:05'],
        [0, 'R0-wait', 'No action: re-measure was similar, watching.', '吃了药', '08:58'],
        [1, 'R1-ask', 'Ask: first reading above usual. Asked to re-measure.', '早', '09:01'],
      ]),
    },
    {
      senior: S.siti,
      status: 'no_contact',
      line: 'No reply for 3 days and almost no movement. No rain or haze.',
      last_checkin: '2026-10-10T09:30:00+08:00',
      handover: sitiHandover,
      alert_this_week: true,
      log: log(S.siti.id, [
        [4, 'R4-no-contact', 'Hand over: no reply and low movement on 3 days, not explained by rain or haze.', null],
        [1, 'R1-ask', 'Ask: no reply, low movement. Second check-in sent.', null],
        [1, 'R1-ask', 'Ask: no reply. Check-in sent again at noon.', null],
        quietDay('Morning! Took my medicine. Going to the market.'),
        quietDay('Ok, medicine taken.'),
        quietDay('Good morning. Cooking for my neighbour today.'),
        quietDay('Taken already.'),
      ]),
    },
    {
      senior: S.raj,
      status: 'note',
      line: 'Missed his pill on 2 days this week. Noted, no action needed yet.',
      last_checkin: '2026-10-13T10:05:00+08:00',
      handover: null,
      alert_this_week: true,
      log: log(S.raj.id, [
        quietDay('Morning, took it. Walking later.'),
        [3, 'R3-missed-doses', 'Note: second missed dose this week.', 'Forgot again lah, will take now', '10:05'],
        quietDay('Taken.'),
        [2, 'R2-suggest', 'Suggest: keep the pills next to the kettle.', 'Ok can try', '09:40'],
        [1, 'R1-ask', 'Ask: missed dose.', 'Oops forgot', '11:20'],
        quietDay('Took already.'),
        quietDay('Good morning, taken.'),
      ]),
    },
    {
      senior: S.lim,
      status: redflag ? 'red_flag' : 'quiet',
      line: redflag ? 'Mentioned chest pain this morning.' : 'Quiet. Low movement on Thursday, but it rained.',
      last_checkin: '2026-10-13T09:18:00+08:00',
      handover: redflag ? limRedFlag : null,
      alert_this_week: false,
      log: log(S.lim.id, [
        redflag
          ? ['R', 'RF-symptom', 'Red flag: chest pain reported. Told to call 995. Staff notified.', '今天还好，就是胸口有点痛', '09:18']
          : quietDay('早上好，药吃了'),
        quietDay('吃了，今天去练气功'),
        quietDay('吃了'),
        quietDay('吃了'),
        quietDay('吃了'),
        [0, 'R0-rain', 'No action: low movement explained by rain (NEA rainfall, nearest station).', '下雨，在家', '09:30'],
        quietDay('早'),
      ]),
    },
    {
      senior: S.wong,
      status: 'quiet',
      line: 'Quiet. Mahjong at a neighbour’s on Saturday: low steps, good company.',
      last_checkin: '2026-10-13T09:45:00+08:00',
      handover: null,
      alert_this_week: false,
      log: log(S.wong.id, [
        quietDay('吃了药'),
        quietDay('吃了'),
        quietDay('吃了'),
        [0, 'R0-social', 'No action: low movement but a social day (mahjong).', '打麻将打了一整天', '09:50'],
        quietDay('吃了'),
        quietDay('吃了，去巴刹'),
        quietDay('吃了'),
      ]),
    },
    {
      senior: S.chua,
      status: 'quiet',
      line: 'Quiet week.',
      last_checkin: '2026-10-13T07:40:00+08:00',
      handover: null,
      alert_this_week: false,
      log: log(S.chua.id, DAYS.map(() => quietDay('吃了，去做早操'))),
    },
    {
      senior: S.tan,
      status: 'quiet',
      line: 'Quiet week. Said she is coming to communal lunch today.',
      last_checkin: '2026-10-13T09:05:00+08:00',
      handover: null,
      alert_this_week: false,
      log: log(S.tan.id, DAYS.map((_, i) => quietDay(i === 0 ? 'Morning, medicine taken. Coming for lunch at the centre.' : 'Morning, medicine taken.'))),
    },
  ];
  return r;
}

const ORDER: Record<CaseloadRow['status'], number> = { red_flag: 0, handover: 1, no_contact: 2, note: 3, quiet: 4 };

export const sampleProgrammes: Programme[] = [
  { id: 'p1', day: 'Mon', start: '09:00', title: 'Morning exercise', place: 'Void deck, Blk 123', indoor: false, sample: true },
  { id: 'p2', day: 'Tue', start: '11:30', title: 'Communal lunch', place: 'Activity room', indoor: true, sample: true },
  { id: 'p3', day: 'Wed', start: '14:00', title: 'Karaoke afternoon', place: 'Activity room', indoor: true, sample: true },
  { id: 'p4', day: 'Thu', start: '10:00', title: 'Health talk: knowing your blood pressure', place: 'Activity room', indoor: true, sample: true },
  { id: 'p5', day: 'Fri', start: '15:00', title: 'Arts and crafts', place: 'Activity room', indoor: true, sample: true },
  { id: 'p6', day: 'Sat', start: '08:30', title: 'Qigong', place: 'Park next to Blk 125', indoor: false, sample: true },
];

const PROG_KEY = 'careloop-mock-programmes';

export function loadProgrammes(): Programme[] {
  try {
    const saved = localStorage.getItem(PROG_KEY);
    if (saved) return JSON.parse(saved);
  } catch {
    /* fall through to samples */
  }
  return sampleProgrammes;
}

export function saveProgrammes(p: Programme[]): Promise<Programme[]> {
  try {
    localStorage.setItem(PROG_KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable: kept for this page only */
  }
  return delay(p);
}

export function getCaseload(contactId: string): Promise<AacCaseload> {
  const contact = staff.find((c) => c.id === contactId) ?? staff[0];
  const redflag = new URLSearchParams(window.location.search).get('scenario') === 'redflag';
  const withClaims = rows(redflag).map((row) => ({
    ...row,
    handover: row.handover ? applyClaims([row.handover])[0] : null,
  }));
  withClaims.sort((a, b) => ORDER[a.status] - ORDER[b.status]);
  return delay({
    contact,
    centre: { name: 'Bishan Lane AAC (sample)' },
    colleagues: staff.filter((c) => c.id !== contact.id),
    as_of: '2026-10-13',
    rows: withClaims,
    programmes: loadProgrammes(),
    synthetic: true,
  });
}
