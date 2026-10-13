// Caregiver-app API client. Set VITE_API_URL to hit the real backend; without it, calls are served by
// in-browser mocks with the same shapes (web/care/mock.ts, web/care/mockAac.ts).
import type {
  BriefData,
  Caseload,
  FamilyView,
  Handover,
  LogDay,
  PairCodeIn,
  PairCodeOut,
  Programme,
  ProgrammeIn,
} from './contract';
import * as mock from '../care/mock';
import * as mockAac from '../care/mockAac';

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

// Demo only: move the demo clock, or reseed.
export function demoAdvance(days: number): Promise<{ today: string }> {
  return BASE ? http('/demo/advance', { method: 'POST', body: JSON.stringify({ days }) }) : Promise.reject(new Error('Demo controls need the API'));
}

export function demoReset(): Promise<{ today: string }> {
  return BASE ? http('/demo/reset', { method: 'POST' }) : Promise.reject(new Error('Demo controls need the API'));
}
