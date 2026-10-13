// Front-end mirror of contracts/. Field names follow the shared contract objects.
// Until Vibu freezes contracts/ (Tue 23:00) this is our best guess; reconcile after the freeze.

export type Rung = 0 | 1 | 2 | 3 | 4 | 'R';
export type Lang = 'en' | 'zh';
export type ConsentShare = 'nothing' | 'digest' | 'readings';

export interface Senior {
  id: string;
  name: string;
  language: Lang;
  home_postal_code: string;
  region: 'north' | 'south' | 'east' | 'west' | 'central';
  conditions: string[];
  medicines: { name: string; dose: string; times: string[] }[];
  likes: string[];
  consent: { family_sees: ConsentShare };
}

export interface Contact {
  id: string;
  senior_id: string;
  role: 'family' | 'aac';
  primary: boolean;
  name: string;
}

export interface Reading {
  senior_id: string;
  time: string; // ISO 8601
  kind: 'bp' | 'hr' | 'steps' | 'sleep';
  values: Record<string, number>; // bp: { systolic, diastolic }
  source: 'cuff' | 'watch' | 'voice' | 'synthetic';
  confidence: number;
}

export interface Decision {
  senior_id: string;
  date: string; // YYYY-MM-DD
  rung: Rung;
  rule_id: string;
  reason: string;
  inputs_used: string[];
}

export interface HandoverOption {
  id: string;
  label: string;
}

export interface Handover {
  id: string;
  senior_id: string;
  kind: 'drift' | 'adherence' | 'no_contact' | 'red_flag';
  opened_at: string;
  evidence: {
    summary: string;
    since: string; // date the pattern started
    tried: { date: string; rung: Rung; what: string }[];
    bp_series?: { date: string; systolic: number; diastolic: number }[];
    baseline?: { systolic: number; diastolic: number };
    reported?: { time: string; words: string; reading?: { systolic: number; diastolic: number } };
  };
  options: HandoverOption[];
  claimed_by: string | null; // contact id
  claimed_by_name: string | null;
  claimed_at: string | null;
  chosen_option: string | null;
}

// GET /care/family/{contact}
export interface FamilyView {
  contact: Contact;
  senior: Senior;
  family: Contact[]; // every family contact for this senior
  status: { week_line: string; rung_today: Rung; as_of: string };
  digest: { week_of: string; lines: string[] } | null;
  handovers: Handover[];
  synthetic: boolean;
}

export interface CheckIn {
  senior_id: string;
  time: string;
  raw_text: string;
  language: Lang | 'singlish';
  extracted_facts: Record<string, unknown>; // shape owned by Mingyu (understand())
}

// One day of the decision log, joined with that day's check-in. Feeds the AAC befriending record.
export interface LogDay {
  decision: Decision;
  checkin: CheckIn | null;
}

export type CaseloadStatus = 'red_flag' | 'handover' | 'no_contact' | 'note' | 'quiet';

export interface CaseloadRow {
  senior: Senior;
  status: CaseloadStatus;
  line: string; // one plain line on why the row sits where it does
  last_checkin: string | null;
  handover: Handover | null;
  alert_this_week: boolean; // at most one non-urgent alert per senior per week
  log: LogDay[]; // last 7 days, newest first
}

export interface Programme {
  id: string;
  day: 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
  start: string; // HH:MM
  title: string;
  place: string;
  indoor: boolean;
  sample: boolean; // seeded demo programme, not a real timetable
}

// GET /care/aac/{contact}/caseload
export interface AacCaseload {
  contact: Contact;
  centre: { name: string };
  colleagues: Contact[]; // other AAC staff who can claim handovers
  as_of: string;
  rows: CaseloadRow[];
  programmes: Programme[];
  synthetic: boolean;
}
