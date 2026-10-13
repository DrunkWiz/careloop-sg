// Shared by the family and AAC views: live reloading, routing, and red flags seen without a handover.
import { useEffect, useState } from 'react';

const REFRESH_MS = 15_000;
export const REFRESH_EVENT = 'careloop:refresh';

// Reloads on a timer, when the tab comes back, when the demo clock moves, and (mocks) when another tab claims.
export function useLive(load: () => void) {
  useEffect(() => {
    load();
    const t = window.setInterval(() => document.visibilityState === 'visible' && load(), REFRESH_MS);
    const onVisible = () => document.visibilityState === 'visible' && load();
    window.addEventListener('storage', load);
    window.addEventListener(REFRESH_EVENT, load);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(t);
      window.removeEventListener('storage', load);
      window.removeEventListener(REFRESH_EVENT, load);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [load]);
}

export function useRoute<R>(parse: () => R): R {
  const [route, setRoute] = useState<R>(parse);
  useEffect(() => {
    const onPop = () => setRoute(parse());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [parse]);
  return route;
}

// Red-flag messages the person has acknowledged when there was no handover to claim. Per browser tab.
const SEEN_KEY = 'careloop-seen-red-flags';
export function seenRedFlags(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) ?? '[]'));
  } catch {
    return new Set();
  }
}
export function markRedFlagSeen(id: string) {
  const s = seenRedFlags();
  s.add(id);
  try {
    sessionStorage.setItem(SEEN_KEY, JSON.stringify([...s]));
  } catch {
    /* storage unavailable: it shows again on reload */
  }
}

