// Caregiver-app API client. Set VITE_API_URL to hit the real backend; without it, calls are served by
// in-browser mocks with the same shapes (web/care/mock.ts, web/care/mockAac.ts).
import type {
  Activities,
  BriefData,
  CaregiverView,
  CareNotes,
  Contact,
  Insights,
  Caseload,
  FamilyView,
  Handover,
  HealthSyncResult,
  HealthSyncView,
  MedicinesView,
  PreventionView,
  ProgrammeFeed,
  TimetableImport,
  LogDay,
  PairCodeIn,
  PairCodeOut,
  PairIn,
  PairOut,
  Programme,
  ProgrammeIn,
  RotaView,
  VentPost,
} from './contract';
import * as mock from '../care/mock';
import * as mockAac from '../care/mockAac';
import * as mockInsights from '../care/mockInsights';

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '');

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, `${init?.method ?? 'GET'} ${path}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const usingMocks = !BASE;

export function getFamilyView(contactId: string): Promise<FamilyView> {
  return BASE ? http(`/care/family/${contactId}`) : mock.getFamilyView(contactId);
}

// GET /care/caregiver/{caregiver_id}: one caregiver's linked seniors (the switcher).
export function getCaregiverView(caregiverId: string): Promise<CaregiverView> {
  return BASE ? http(`/care/caregiver/${caregiverId}`) : mock.getCaregiverView(caregiverId);
}

// POST /care/contact/{contact_id}/primary: promote this contact to primary.
export function setPrimary(contactId: string): Promise<Contact> {
  return BASE ? http(`/care/contact/${contactId}/primary`, { method: 'POST' }) : mock.setPrimary(contactId);
}

// GET /senior/{sid}/rota
export function getRota(seniorId: string): Promise<RotaView> {
  return BASE ? http(`/senior/${seniorId}/rota`) : mock.getRota(seniorId);
}

// PUT /senior/{sid}/rota
export function putRota(seniorId: string, mode: 'weekly' | 'daily', startDate: string, order: string[]): Promise<RotaView> {
  return BASE
    ? http(`/senior/${seniorId}/rota`, { method: 'PUT', body: JSON.stringify({ mode, start_date: startDate, order }) })
    : mock.putRota(seniorId, mode, startDate, order);
}

// POST /senior/{sid}/rota/swap
export function swapRota(seniorId: string, date: string, contactId: string): Promise<RotaView> {
  return BASE
    ? http(`/senior/${seniorId}/rota/swap`, { method: 'POST', body: JSON.stringify({ date, contact_id: contactId }) })
    : mock.swapRota(seniorId, date, contactId);
}

// DELETE /senior/{sid}/rota
export function deleteRota(seniorId: string): Promise<RotaView> {
  return BASE ? http(`/senior/${seniorId}/rota`, { method: 'DELETE' }) : mock.deleteRota(seniorId);
}

export function getCaseload(workerId: string): Promise<Caseload> {
  return BASE ? http(`/care/aac/${workerId}/caseload`) : mockAac.getCaseload(workerId);
}

export function claimHandover(handoverId: string, contactId: string, choice: string): Promise<Handover> {
  return BASE
    ? http(`/handover/${handoverId}/claim`, { method: 'POST', body: JSON.stringify({ contact_id: contactId, choice }) })
    : mock.claimHandover(handoverId, contactId, choice);
}

export function getBrief(seniorId: string): Promise<BriefData> {
  return BASE ? http(`/senior/${seniorId}/brief.json`) : mockAac.getBrief(seniorId);
}

export function briefPdfUrl(seniorId: string): string | null {
  return BASE ? `${BASE}/senior/${seniorId}/brief.pdf` : null;
}

// Added endpoint (needs team OK). Pass the family contact so the senior's consent applies.
// Returns null when the API doesn't have it.
export async function getLog(seniorId: string, days = 14, contactId?: string): Promise<LogDay[] | null> {
  if (!BASE) return seniorId === 'tan' ? mock.getLog(days) : mockAac.getLog(seniorId, days);
  try {
    return await http(`/senior/${seniorId}/log?days=${days}${contactId ? `&contact=${encodeURIComponent(contactId)}` : ''}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

// Added endpoints (need team OK). Pass the family contact so the senior's consent applies.
export function getInsights(seniorId: string, contactId?: string, days = 30): Promise<Insights> {
  return BASE
    ? http(`/senior/${seniorId}/insights?days=${days}${contactId ? `&contact=${encodeURIComponent(contactId)}` : ''}`)
    : mockInsights.getInsights(seniorId);
}

export function getActivities(seniorId: string, contactId?: string): Promise<Activities> {
  return BASE
    ? http(`/senior/${seniorId}/activities${contactId ? `?contact=${encodeURIComponent(contactId)}` : ''}`)
    : mockInsights.getActivities(seniorId);
}

// Added endpoint (needs team OK). Every linked contact reads and writes the same notes.
export function getCareNotes(seniorId: string, contactId: string): Promise<CareNotes> {
  return BASE ? http(`/senior/${seniorId}/care-notes?contact=${encodeURIComponent(contactId)}`) : mock.getCareNotes(seniorId);
}

export function putCareNotes(seniorId: string, contactId: string, notes: CareNotes): Promise<CareNotes> {
  const { updated_by: _b, updated_at: _a, ...body } = notes;
  return BASE
    ? http(`/senior/${seniorId}/care-notes?contact=${encodeURIComponent(contactId)}`, { method: 'PUT', body: JSON.stringify(body) })
    : mock.putCareNotes(seniorId, notes);
}

export function getProgrammes(aacId: string): Promise<Programme[]> {
  return BASE ? http(`/aac/${aacId}/programmes`) : mockAac.getProgrammes(aacId);
}

export function putProgrammes(aacId: string, programmes: ProgrammeIn[]): Promise<Programme[]> {
  return BASE
    ? http(`/aac/${aacId}/programmes`, { method: 'PUT', body: JSON.stringify(programmes) })
    : mockAac.putProgrammes(aacId, programmes);
}

export function createPairCode(body: PairCodeIn): Promise<PairCodeOut> {
  return BASE ? http('/care/pair-code', { method: 'POST', body: JSON.stringify(body) }) : mock.createPairCode(body);
}

export function pair(body: PairIn): Promise<PairOut> {
  return BASE ? http('/pair', { method: 'POST', body: JSON.stringify(body) }) : mock.pair(body);
}

// Demo only: move the demo clock, or reseed.
export function demoAdvance(days: number): Promise<{ today: string }> {
  return BASE ? http('/demo/advance', { method: 'POST', body: JSON.stringify({ days }) }) : Promise.reject(new Error('Demo controls need the API'));
}

export function demoReset(): Promise<{ today: string }> {
  return BASE ? http('/demo/reset', { method: 'POST' }) : Promise.reject(new Error('Demo controls need the API'));
}

// --- vent space: anonymous caregiver rant room (no caregiver_id or senior_id saved) ----------

export function getVentFeed(): Promise<VentPost[]> {
  return BASE ? http('/vent') : mock.getVentFeed();
}

export function postVent(nickname: string, text: string): Promise<VentPost> {
  return BASE ? http('/vent', { method: 'POST', body: JSON.stringify({ nickname, text }) }) : mock.postVent(nickname, text);
}

export function hugVentPost(postId: string): Promise<VentPost> {
  return BASE ? http(`/vent/${postId}/hug`, { method: 'POST' }) : mock.hugVentPost(postId);
}

export function reportVentPost(postId: string): Promise<{ id: string; hidden: boolean }> {
  return BASE ? http(`/vent/${postId}/report`, { method: 'POST' }) : mock.reportVentPost(postId);
}

// Added endpoints (need team OK): health apps on the senior's phone. Mocks show Mr Tan's phone, read-only.
export function getHealthSync(seniorId: string, contactId?: string, days = 7): Promise<HealthSyncView> {
  return BASE
    ? http(`/senior/${seniorId}/health-sync?days=${days}${contactId ? `&contact=${encodeURIComponent(contactId)}` : ''}`)
    : mock.getHealthSync(seniorId, days);
}

// Demo only: stands in for the senior's phone syncing now, with an optional cuff measurement.
export function demoHealthSync(seniorId: string, bp?: [number, number]): Promise<HealthSyncResult> {
  return http(`/demo/health-sync/${seniorId}`, { method: 'POST', body: JSON.stringify(bp ? { bp } : {}) });
}

// Added endpoints (need team OK): import a centre's own calendar (.ics) or spreadsheet (.csv).
export function importTimetable(aacId: string, body: { text?: string; url?: string; save?: boolean }): Promise<TimetableImport> {
  return BASE
    ? http(`/aac/${aacId}/programmes/import`, { method: 'POST', body: JSON.stringify(body) })
    : Promise.reject(new ApiError(501, 'Importing needs the API (npm run dev:live).'));
}

export async function getProgrammeFeed(aacId: string): Promise<ProgrammeFeed | null> {
  return BASE ? http(`/aac/${aacId}/programmes/feed`) : null;
}

export function stopProgrammeFeed(aacId: string): Promise<null> {
  return http(`/aac/${aacId}/programmes/feed`, { method: 'DELETE' });
}

// Added endpoints (need team OK): what each medicine is for, and vaccines and check-ups that are due.
const q = (contactId?: string, lang?: string) =>
  [contactId && `contact=${encodeURIComponent(contactId)}`, lang && `lang=${lang}`].filter(Boolean).join('&');

export function getMedicines(seniorId: string, contactId?: string, lang = 'en'): Promise<MedicinesView> {
  return BASE ? http(`/senior/${seniorId}/medicines?${q(contactId, lang)}`) : mock.getMedicines();
}

export function getPrevention(seniorId: string, contactId?: string, lang = 'en'): Promise<PreventionView> {
  return BASE ? http(`/senior/${seniorId}/prevention?${q(contactId, lang)}`) : mock.getPrevention();
}
