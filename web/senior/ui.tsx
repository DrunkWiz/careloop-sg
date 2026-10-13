// Small building blocks for the senior app: big buttons, the mic, icons, a toast.
import type { ReactNode } from 'react';
import { useT } from '../shared/i18n';

export function BigButton({ icon, label, onClick, done, tone = 'plain', disabled }: {
  icon?: ReactNode; label: string; onClick: () => void; done?: boolean; tone?: 'plain' | 'primary' | 'alert'; disabled?: boolean;
}) {
  return (
    <button className={`sa-big sa-${tone}${done ? ' sa-done' : ''}`} onClick={onClick} disabled={disabled}>
      {icon && <span className="sa-big-icon" aria-hidden>{icon}</span>}
      <span>{label}</span>
      {done && <span className="sa-check" aria-hidden>{Icon.check}</span>}
    </button>
  );
}

export function TalkButton({ listening, onStart, onStop, label }: {
  listening: boolean; onStart: () => void; onStop: () => void; label: string;
}) {
  return (
    <button
      className={`sa-talk${listening ? ' sa-listening' : ''}`}
      onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); onStart(); }}
      onPointerUp={onStop}
      onPointerCancel={onStop}
      onContextMenu={(e) => e.preventDefault()}
      // Keyboard and switch users: Space/Enter toggles instead of holding.
      onKeyDown={(e) => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { e.preventDefault(); listening ? onStop() : onStart(); } }}
      aria-pressed={listening}
    >
      <span className="sa-talk-icon" aria-hidden>{Icon.mic}</span>
      <span>{label}</span>
    </button>
  );
}

export function Screen({ title, onBack, children }: { title: string; onBack?: () => void; children: ReactNode }) {
  const t = useT();
  return (
    <section className="sa-screen">
      <header className="sa-screen-head">
        {onBack && (
          <button className="sa-back" onClick={onBack}>
            <span aria-hidden>{Icon.back}</span> {t('common.back')}
          </button>
        )}
        <h1>{title}</h1>
      </header>
      {children}
    </section>
  );
}

export function Toast({ text }: { text: string | null }) {
  return <div className={`sa-toast${text ? ' sa-show' : ''}`} role="status" aria-live="polite">{text}</div>;
}

const svg = (d: ReactNode) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

export const Icon = {
  pill: svg(<><rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-35 12 12)" /><path d="M9.5 8.5l5 7" /></>),
  heart: svg(<><path d="M20.8 8.6a5 5 0 0 0-8.8-3.2 5 5 0 0 0-8.8 3.2c0 5.4 8.8 10.4 8.8 10.4s8.8-5 8.8-10.4z" /><path d="M3.5 12h4l2-3 3 6 2-3h6" /></>),
  smile: svg(<><circle cx="12" cy="12" r="9" /><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0" /><path d="M9 9.5h.01M15 9.5h.01" /></>),
  mic: svg(<><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>),
  check: svg(<path d="M5 12.5l4.5 4.5L19 7.5" />),
  back: svg(<path d="M15 5l-7 7 7 7" />),
  phone: svg(<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />),
  cloud: svg(<path d="M7 18h10a4 4 0 0 0 .5-8 6 6 0 0 0-11.5 1.5A3.3 3.3 0 0 0 7 18z" />),
  list: svg(<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />),
  x: svg(<path d="M6 6l12 12M18 6L6 18" />),
};
