// API client. Set VITE_API_URL to hit the real backend; without it, calls are served by local mocks.
import type { FamilyView, Handover } from './contract';
import * as mock from '../care/mock';

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
