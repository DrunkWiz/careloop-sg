// Senior app's API client. Talks to Vibu's API when VITE_API_URL is set; otherwise to an
// in-browser mock (mock.ts) so the app works before the contract freezes and without a backend.
import type { Lang } from '../shared/i18n';
import type { CheckInResult, Consent, KnownFact, PairResult, ReadingResult, Today } from './types';
import type { MedicinesView, PreventionView } from '../shared/contract';
import { mock } from './mock';
import { getMedicines as mockMedicines, getPrevention as mockPrevention } from '../care/mock';

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '');
export const usingMock = !BASE;

async function http<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${path}: ${res.status}`);
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  /** lang: what the app is showing now, so the prompt and haze text come back in that language. */
  today: (seniorId: string, lang?: Lang): Promise<Today> =>
    usingMock ? mock.today(seniorId) : http('GET', `/senior/${seniorId}/today${lang ? `?lang=${encodeURIComponent(lang)}` : ''}`),

  /** Every check-in goes here as text: speech is transcribed in the browser; the big buttons send canned text. */
  checkin: (seniorId: string, text: string, lang: Lang, source: 'voice' | 'typed' | 'button'): Promise<CheckInResult> =>
    usingMock
      ? mock.checkin(seniorId, text, lang)
      : http('POST', '/checkin', { senior_id: seniorId, text, language: lang, source }),

  reading: (seniorId: string, bp: { systolic: number; diastolic: number; pulse?: number | null }, source: 'cuff' | 'voice'): Promise<ReadingResult> =>
    usingMock
      ? mock.reading(seniorId, bp).then(() => ({ message: null, rung: '0' as const }))
      : http('POST', '/reading', {
          senior_id: seniorId,
          kind: 'bp',
          values: bp,
          source,
          confidence: 1, // confirmed by the senior
        }),

  knows: (seniorId: string): Promise<KnownFact[]> =>
    usingMock ? mock.knows(seniorId) : http('GET', `/senior/${seniorId}/knows`),

  // Added endpoints (Nathan, need team OK): what each medicine is for, and vaccines and check-ups due.
  medicines: (seniorId: string, lang: Lang): Promise<MedicinesView> =>
    usingMock ? mockMedicines() : http('GET', `/senior/${seniorId}/medicines?lang=${lang}`),

  prevention: (seniorId: string, lang: Lang): Promise<PreventionView> =>
    usingMock ? mockPrevention() : http('GET', `/senior/${seniorId}/prevention?lang=${lang}`),

  forget: (seniorId: string, factId: string): Promise<void> =>
    usingMock ? mock.forget(seniorId, factId) : http('DELETE', `/senior/${seniorId}/knows/${encodeURIComponent(factId)}`),

  // NOT IN THE CONTRACT YET (raise with Vibu): recording "Not for me" on a suggestion, and pairing.
  notForMe: (seniorId: string, suggestionId: string): Promise<void> =>
    usingMock
      ? mock.notForMe(seniorId, suggestionId)
      : http('POST', `/senior/${seniorId}/suggestions/${encodeURIComponent(suggestionId)}/response`, { response: 'not_for_me' }),

  pair: (code: string, lang: Lang, consent: Consent, seniorId?: string | null): Promise<PairResult> =>
    usingMock
      ? mock.pair(code, lang, consent)
      : http('POST', '/pair', { code, language: lang, consent, ...(seniorId ? { senior_id: seniorId } : {}) }),
};
