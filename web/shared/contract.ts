// Front-end mirror of contracts/schemas (frozen 13 Oct 23:00) and the API responses in backend/api/app.py.
// Field names and enums match the schemas exactly. If a schema changes, change it here too.

export type Rung = '0' | '1' | '2' | '3' | '4' | 'R';
export type Lang = 'en' | 'en-SG' | 'zh';
export type FamilySees = 'nothing' | 'digest' | 'readings';

export interface Medicine {
  name: string;
  dose_text: string; // as on the label; CareLoop never changes it
  schedule: ('morning' | 'noon' | 'evening' | 'night')[];
  started: string;
  for_bp: boolean;
}

export interface Senior {
  id: string;
  name: string;
  language: Lang;
  home_postal: string;
  region: 'north' | 'south' | 'east' | 'west' | 'central';
  path: 'family' | 'aac';
  aac_id: string | null;
  conditions: string[];
  medicines: Medicine[];
  likes: string[];
  usual_checkin_time: string;
  consent: { family_sees: FamilySees; share_words: boolean; share_activity: boolean };
  hidden_suggestions: string[];
}

// The cut-down senior the care endpoints return.
export interface SeniorRef {
  id: string;
  name: string;
  language: Lang;
}

export interface Contact {
  id: string;
  senior_id: string;
  role: 'family' | 'aac';
  primary: boolean;
  name: string;
  language: Lang;
  worker_id: string | null; // groups an AAC caseload
}

export interface Message {
  id: string;
  senior_id: string;
  decision_id: string | null;
  to: 'senior' | 'family' | 'aac';
  contact_id: string | null;
  rung: Rung;
  language: Lang;
  text: string;
  from_template: boolean;
  guardrail: { passed: boolean; reasons: string[] };
  model: string | null;
  time: string;
}

export type HandoverKind =
  | 'bp_drift'
  | 'missed_medicine'
  | 'unwell'
  | 'activity'
  | 'no_contact'
  | 'double_dose'
  | 'red_flag';

export interface BpPoint {
  date: string;
  systolic: number | null;
  diastolic: number | null;
}

export interface Handover {
  id: string;
  senior_id: string;
  decision_id: string;
  opened_at: string;
  kind: HandoverKind;
  evidence: {
    summary: string;
    bp_series: BpPoint[]; // empty when the senior hasn't agreed to share readings (applied by the server)
    baseline: { systolic: number; diastolic: number } | null;
    dates: string[];
    tried: { date: string; rung: Rung; what: string }[];
  };
  options: { id: string; label: string }[];
  status: 'open' | 'claimed';
  claimed_by: string | null; // contact id
  claimed_at: string | null;
  choice: string | null;
  claimed_by_name?: string | null; // added by GET /care/family
}

// GET /care/family/{contact}: the numbers behind the weekly digest. The app turns them into words.
export interface Digest {
  week_start: string;
  week_end: string;
  headline: 'quiet' | 'worth a look' | 'needs you';
  readings_days: number;
  mean_systolic: number | null; // null unless family_sees is "readings"
  mean_diastolic: number | null;
  baseline: { systolic: number; diastolic: number } | null;
  pills_taken_days: number;
  missed_days: number;
  checkin_days: number;
  social_days: number;
  worth_raising: string[];
}

export interface FamilyView {
  contact: Contact;
  senior: SeniorRef;
  family_sees: FamilySees;
  today: string;
  status: 'quiet' | 'handover' | 'red_flag';
  digest: Digest | null; // null when family_sees is "nothing"
  handovers: Handover[];
  red_flags: Message[]; // rung R messages to family in the last 2 days
  other_contacts: { id: string; name: string }[];
}

// GET /care/aac/{worker_id}/caseload
export interface CaseloadRow {
  senior: SeniorRef;
  contact_id: string; // this worker's contact for this senior: claim with it
  status: 'quiet' | 'handover' | 'red_flag';
  today: { rung: Rung | null; reason: string | null };
  handover: Handover | null;
  last_reply: string | null;
}

export interface Caseload {
  worker_id: string;
  today: string;
  seniors: CaseloadRow[];
}

// GET/PUT /aac/{aac_id}/programmes
export type Weekday = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

export interface ProgrammeIn {
  title: string;
  title_zh?: string | null;
  weekdays: Weekday[];
  time: string;
  tags: string[];
  indoor: boolean;
  free: boolean;
}

export interface Programme extends ProgrammeIn {
  id: string;
  place_id: string;
  sample: boolean;
}

// GET /senior/{id}/brief.json (the parts the care app reads)
export interface BriefData {
  senior: { id: string; name: string; conditions: string[]; medicines: Medicine[] };
  period: { from: string; to: string };
  aac: { id: string; name: string | null; going: string[] } | null;
}

// GET /senior/{id}/log?days=N&contact=… (added, needs team OK): every day's decision, newest first.
// For a family contact the senior's consent applies: null means "not shared" (or no decision that day).
export interface LogDay {
  date: string;
  rung: Rung | null;
  rule_id: string | null;
  reason: string | null; // engine wording; only when readings are shared, or on a red flag
  decision_id: string | null;
  checkins: { time: string; raw_text: string; language: Lang }[]; // only when words are shared
  replied: boolean | null;
  pills: 'taken' | 'missed' | null;
  social: boolean | null;
  bp: { systolic: number; diastolic: number } | null;
  psi: number | null;
  rain_mm: number | null;
  festival: string | null;
}

// POST /care/pair-code
export interface PairCodeIn {
  contact_name: string;
  role: 'family' | 'aac';
  language?: Lang;
  senior_name: string;
  home_postal: string;
  worker_id?: string | null;
}

export interface PairCodeOut {
  code: string;
  senior_id: string;
  contact_id: string;
}

// GET /senior/{id}/insights?days=30&contact=… (added, needs team OK): patterns in the senior's own data.
export interface Finding {
  id: string;
  tone: 'watch' | 'good' | 'neutral';
  title: string;
  detail: string;
  n: number; // how many days or readings it rests on
}

export interface Insights {
  period: { from: string; to: string; days: number };
  bp: {
    shared: boolean;
    series: BpPoint[];
    baseline: { systolic: number; diastolic: number; fallback: boolean } | null;
    last7_systolic: number | null;
    prev7_systolic: number | null;
    slope_per_week: number | null;
    trend: 'rising' | 'falling' | 'steady' | 'unclear';
    days_over_140: number | null;
    readings_days: number;
  };
  adherence: {
    reported_days: number;
    taken_days: number;
    missed_days: number;
    streak_days: number;
    by_weekday: { day: Weekday; missed: number; reported: number }[];
    calendar: { date: string; pills: 'taken' | 'missed' | null }[];
  };
  activity: {
    steps: { date: string; steps: number | null }[];
    steps_baseline: number | null;
    steps_last7_avg: number | null;
    social_days_last7: number;
    social_days_prev7: number;
  } | null;
  checkins: { replied_days: number; days: number; usual_time: string; median_first_time: string | null };
  context: { rain_days: number; haze_days: number; festival_days: number };
  findings: Finding[];
  medicines: Medicine[];
  running_low: { date: string; items: string[] }[];
  note: string;
}

// GET /senior/{id}/activities?contact=… (added, needs team OK)
export interface Place {
  id: string;
  kind: 'aac' | 'cc';
  name: string;
  address: string | null;
  postal: string | null;
  km: number;
  lat: number;
  lon: number;
}

export interface Activities {
  today: string;
  weekday: Weekday;
  indoor_only: boolean;
  why_indoor: 'rain' | 'haze' | null;
  psi: number | null;
  rain_mm: number | null;
  likes: string[];
  distance_from: string;
  own_aac: {
    id: string;
    name: string;
    address: string | null;
    programmes: (ProgrammeIn & { id: string; sample: boolean; fits: string | null; today: boolean; hidden: boolean })[];
  } | null;
  nearby_aacs: Place[];
  nearby_ccs: Place[];
  suggested_today: { place: string; kind: string; why_it_fits: string; indoor: boolean; sample: boolean; as_told_to_senior?: string }[];
  suggestions: { id: string; date: string; place: string; kind: string; why_it_fits: string; indoor: boolean; sample: boolean; response: 'going' | 'not_for_me' | null }[];
  source: string;
}

// GET/PUT /senior/{id}/care-notes?contact=… (added, needs team OK): kept together by every linked contact.
export interface Appointment {
  id: string;
  date: string;
  time?: string | null;
  place: string;
  purpose: string;
  who_goes?: string | null;
  notes_after: string;
}

export interface Question {
  id: string;
  text: string;
  by: string;
  added: string;
  asked: boolean;
  answer: string;
}

export interface Task {
  id: string;
  title: string;
  due?: string | null;
  owner?: string | null;
  done: boolean;
  done_by?: string | null;
}

export interface CareNotes {
  appointments: Appointment[];
  questions: Question[];
  tasks: Task[];
  emergency: { allergies: string; gp_name: string; gp_phone: string; home_address: string; notes: string };
  updated_by?: string | null;
  updated_at?: string | null;
}

// GET /senior/{id}/health-sync (added: Nathan, needs team OK). Apple Health or Health Connect on the senior's phone.
export interface HealthSyncStatus {
  platform: 'health_connect' | 'healthkit';
  platform_name: string;
  apps: string[];
  kinds: string[];
  last_sync: string;
  last_batch: { records: number; readings: number; skipped: number };
}

export interface HealthSyncDay {
  date: string;
  steps: number | null;
  resting_hr: number | null;
  sleep_hours: number | null;
  bp: { time: string; systolic: number; diastolic: number }[];
}

export interface HealthSyncView {
  connected: boolean;
  status: HealthSyncStatus | null;
  days: HealthSyncDay[];
  shares_readings: boolean;
  shares_activity: boolean;
}

// POST /senior/{id}/health-sync and POST /demo/health-sync/{id}
export interface HealthSyncResult {
  status: HealthSyncStatus;
  imported: Record<string, number>;
  days: string[];
  skipped: number;
  rung: Rung | null;
  message: { text: string } | null;
}

// POST /aac/{id}/programmes/import (added: Nathan, needs team OK)
export interface ProgrammeFeed {
  url: string;
  pulled_at: string;
  error: string | null;
  count: number;
  warnings: string[];
}

export interface TimetableImport {
  programmes: ProgrammeIn[];
  warnings: string[];
  saved: boolean;
  feed: ProgrammeFeed | null;
}
