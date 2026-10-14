// Makes each front door installable as its own phone app ("Add to Home Screen"): the senior app, the family
// app and the centre console each get their own name, icon and start page. The public home page and the
// /care chooser stay ordinary web pages.
export type AppDoor = 'senior' | 'family' | 'centre';

const DOORS: Record<AppDoor, { manifest: string; title: string; theme: string; icon: string }> = {
  senior: { manifest: '/senior.webmanifest', title: 'CareLoop', theme: '#f5f7f2', icon: '/icons/green-180.png' },
  family: { manifest: '/family.webmanifest', title: 'CareLoop', theme: '#f5f7f2', icon: '/icons/green-180.png' },
  centre: { manifest: '/centre.webmanifest', title: 'CL Centres', theme: '#23264f', icon: '/icons/navy-180.png' },
};

export function doorFor(path: string, search: string): AppDoor | null {
  if (path.startsWith('/senior')) return 'senior';
  if (path.startsWith('/care/aac')) return 'centre';
  if (path.startsWith('/care/family') || /^\/care\/(handover|pair)/.test(path) || new URLSearchParams(search).has('contact')) return 'family';
  return null;
}

function meta(name: string, content: string) {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.name = name;
    document.head.appendChild(el);
  }
  el.content = content;
}

function link(rel: string, href: string) {
  const el = document.createElement('link');
  el.rel = rel;
  el.href = href;
  document.head.appendChild(el);
}

export function setUpApp(door: AppDoor | null) {
  if (door) {
    const d = DOORS[door];
    link('manifest', d.manifest);
    link('apple-touch-icon', d.icon);
    meta('theme-color', d.theme);
    meta('apple-mobile-web-app-title', d.title);
  }
  // Production builds only: in development a saved copy would hide your edits.
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        /* the app works without it, just not offline */
      });
    });
  }
}

// --- Installing ------------------------------------------------------------------------------

interface InstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferred: InstallPromptEvent | null = null;
const listeners = new Set<() => void>();
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault(); // keep it for our own button
  deferred = e as InstallPromptEvent;
  listeners.forEach((f) => f());
});
window.addEventListener('appinstalled', () => {
  deferred = null;
  listeners.forEach((f) => f());
});

export const isInstalled = () =>
  window.matchMedia('(display-mode: standalone)').matches || (navigator as { standalone?: boolean }).standalone === true;
export const isIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
export const canPrompt = () => deferred != null;
export const onInstallChange = (f: () => void) => {
  listeners.add(f);
  return () => void listeners.delete(f);
};
export async function promptInstall(): Promise<boolean> {
  if (!deferred) return false;
  await deferred.prompt();
  const { outcome } = await deferred.userChoice;
  deferred = null;
  listeners.forEach((f) => f());
  return outcome === 'accepted';
}
