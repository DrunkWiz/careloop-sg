// What the senior app reads and sends. Mirrors contracts/ once Vibu freezes it (Tue 23:00);
// until then these are our best reading of the shared contract table. Facts and Message match
// backend/language/facts.example.json and message.example.json.
import type { Lang } from '../shared/i18n';

export type Rung = '0' | '1' | '2' | '3' | '4' | 'R';

export interface BP {
  systolic: number;
  diastolic: number;
  pulse: number | null;
  confidence: number;
  span: string;
  plausible: boolean;
  needs_confirmation: boolean;
}

export interface Symptom {
  code: string;
  words: string;
  red_flag: boolean;
}

export interface Facts {
  lang: Lang;
  bp: BP[];
  pulse: number | null;
  doses: { taken: boolean; medicine: string | null; span: string }[];
  running_out: string[];
  symptoms: Symptom[];
  activities: { kind: string; words: string; social_contact: boolean }[];
  mood: 'good' | 'ok' | 'low' | null;
  english: string;
  source: string;
  red_flag: boolean;
  feeling_unwell: boolean;
  social_contact: boolean;
}

export interface Message {
  to: 'senior' | 'family' | 'aac';
  rung: Rung;
  language: Lang;
  text: string;
  from_template: boolean;
  guardrail: { passed: boolean; reasons: string[] };
  model: string | null;
}

export interface CheckInResult {
  checkin_id: string;
  facts: Facts;
  /** The engine's reply to the senior, if any (rung 0 means none). */
  message: Message | null;
}

export interface ReadingResult {
  message: Message | null;
  rung: Rung;
}

export interface Suggestion {
  id: string;
  place: string;
  why_it_fits: string;
  indoor: boolean;
  free?: boolean;
  response: 'not_for_me' | 'going' | null;
}

export interface Today {
  date?: string;
  senior: { id: string; name: string; language: Lang };
  pills_taken: boolean;
  bp_logged: boolean;
  feel_logged: boolean;
  /** Morning check-in is due (at the senior's usual time). */
  checkin_due: boolean;
  /** The engine's question for the check-in, written by write() at rung 1. */
  prompt: Message | null;
  /** The engine's MOH-based text for today's PSI band. Shown as-is, never invented here. */
  haze: { psi: number; band: string; text: string } | null;
  suggestions: Suggestion[];
}

export interface KnownFact {
  id: string;
  text: string;
  kind: 'condition' | 'medicine' | 'like' | 'routine' | 'contact' | 'other';
}

export interface Consent {
  /** What the family sees. Red flags are always shared, and the senior is told so at setup. */
  family_sees: 'nothing' | 'digest' | 'readings';
  share_words: boolean;
  share_activity: boolean;
}

export interface PairResult {
  senior_id: string;
  contact_name: string;
}
