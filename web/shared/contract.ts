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

export interface Caregiver {
  id: string;
  name: string;
  language: Lang;
  role: 'family' | 'aac';
  worker_id: string | null; // AAC staff member, shared across their caseload
}

export interface Contact {
  id: string;
  caregiver_id: string; // the caregiver this link belongs to
  senior_id: string;
  role: 'family' | 'aac';
  primary: boolean;
  name: string; // denormalized from the caregiver
  language: Lang;
  worker_id: string | null; // denormalized from the caregiver
  consent?: { family_sees: FamilySees; share_words: boolean; share_activity: boolean };
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
  on_duty: boolean;
  on_duty_name: string | null;
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

// GET /care/caregiver/{caregiver_id}: a caregiver's linked seniors (one caregiver, many seniors).
export interface CaregiverSenior {
  contact_id: string;
  senior_id: string;
  senior_name: string;
  primary: boolean;
  status: 'quiet' | 'handover' | 'red_flag';
  on_duty: boolean;
}

export interface CaregiverView {
  caregiver: Caregiver;
  seniors: CaregiverSenior[];
}

// GET/PUT /senior/{sid}/rota
export interface Rota {
  id: string;
  senior_id: string;
  mode: 'weekly' | 'daily';
  start_date: string; // YYYY-MM-DD
  order: string[]; // contact ids
  swaps: { date: string; contact_id: string }[];
}

export interface RotaView {
  rota: Rota | null;
  on_duty: { id: string; name: string } | null;
}

// POST /care/pair-code
export interface PairCodeIn {
  caregiver_id?: string | null; // existing caregiver; omit to create a new one
  contact_name: string;
  role: 'family' | 'aac';
  language?: Lang;
  senior_id?: string | null; // existing senior to link to; omit to create a new one
  senior_name: string;
  home_postal: string;
  worker_id?: string | null;
}

export interface PairCodeOut {
  code: string;
  caregiver_id: string;
  senior_id: string;
  contact_id: string;
}

// POST /pair
export interface PairIn {
  code: string;
  language?: Lang;
  consent?: { family_sees: FamilySees; share_words: boolean; share_activity: boolean };
  senior_id?: string | null; // if the device already has a senior, link to it
}

export interface PairOut {
  senior_id: string;
  contact_name: string;
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

// GET /vent (latest 100 visible, newest first), POST /vent
export interface VentPost {
  id: string;
  nickname: string;
  text: string;
  time: string; // ISO datetime
  hugs: number;
  hidden: boolean;
}
