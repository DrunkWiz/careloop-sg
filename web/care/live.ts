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


// While something needs the person: badge the tab title, and (if they turned alerts on) one notification
// per new alert. Only while CareLoop is open in a tab; there is no push service.
export function useAlert(title: string | null, body: string) {
  useEffect(() => {
    const base = 'CareLoop SG';
    document.title = title ? `(!) ${title} · ${base}` : base;
    if (!title) return;
    const key = `careloop-alerted:${title}`;
    try {
      if (sessionStorage.getItem(key)) return;
      sessionStorage.setItem(key, '1');
    } catch {
      /* no storage: may notify again on reload */
    }
    if ('Notification' in window && Notification.permission === 'granted' && document.visibilityState !== 'visible') {
      new Notification(title, { body });
    }
  }, [title, body]);
}

// Bumps when the demo clock moves (or anything else asks for a refresh), so data that isn't polled reloads.
export function useRefreshTick(): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const on = () => setTick((n) => n + 1);
    window.addEventListener(REFRESH_EVENT, on);
    return () => window.removeEventListener(REFRESH_EVENT, on);
  }, []);
  return tick;
}
