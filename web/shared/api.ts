// API client. Set VITE_API_URL to hit the real backend; without it, calls are served by local mocks.
import type { AacCaseload, FamilyView, Handover, Programme } from './contract';
import * as mock from '../care/mock';
import * as mockAac from '../care/mockAac';

const BASE = import.meta.env.VITE_API_URL as string | undefined;

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const usingMocks = !BASE;

export function getFamilyView(contactId: string): Promise<FamilyView> {
  return BASE ? http(`/care/family/${contactId}`) : mock.getFamilyView(contactId);
}

export function claimHandover(handoverId: string, contactId: string, optionId: string): Promise<Handover> {
  return BASE
    ? http(`/handover/${handoverId}/claim`, {
        method: 'POST',
        body: JSON.stringify({ contact_id: contactId, option_id: optionId }),
      })
    : mock.claimHandover(handoverId, contactId, optionId);
}

export function briefPdfUrl(seniorId: string): string | null {
  return BASE ? `${BASE}/senior/${seniorId}/brief.pdf` : null;
}

export function getCaseload(contactId: string): Promise<AacCaseload> {
  return BASE ? http(`/care/aac/${contactId}/caseload`) : mockAac.getCaseload(contactId);
}

// No endpoint in the contract for saving a timetable yet: local-only until one exists.
export function saveProgrammes(_contactId: string, programmes: Programme[]): Promise<Programme[]> {
  return mockAac.saveProgrammes(programmes);
}
