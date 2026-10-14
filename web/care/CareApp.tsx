// The /care app. Owner: Nathan. Two separate front doors, built for two different people:
//   /care/family  the family app: phone-first, warm, one senior, tabs for Today, Health, Activities, Settings.
//   /care/aac     CareLoop for Centres: a work console for AAC staff, many seniors, dense and desktop-friendly.
// /care itself asks which one you are. Until login exists, ?contact= picks the family member and ?worker= the
// AAC worker. Old links (/care?contact=…, /care/handover/…, /care/pair) still open the family app.
import { useCallback, useState } from 'react';
import type { FamilyView, Handover, LogDay } from '../shared/contract';
import { demoAdvance, demoReset, getFamilyView, getLog, usingMocks } from '../shared/api';
import FamilyHome from './FamilyHome';
import HandoverView from './HandoverView';
import RedFlag from './RedFlag';
import Pairing from './Pairing';
import AacApp from './AacApp';
import Health from './Health';
import ActivitiesView from './ActivitiesView';
import RoleChooser from './RoleChooser';
import CarePlan from './CarePlan';
import LookingAfterYou from './LookingAfterYou';
import { REFRESH_EVENT, markRedFlagSeen, seenRedFlags, useAlert, useLive, useRoute } from './live';
import { navigate } from './nav';
import Brand from '../shared/Brand';
import './care.css';
import './themes.css';
import './refresh.css';

export default function CareApp() {
  const params = new URLSearchParams(window.location.search);
  const path = window.location.pathname;
  const door = path.startsWith('/care/aac')
    ? 'centre'
    : path.startsWith('/care/family') || /^\/care\/(handover|pair)/.test(path) || params.has('contact')
      ? 'family'
      : 'choose';

  return (
    <main className={`care theme-${door} ${largeText() ? 'is-large-text' : ''}`}>
      {params.has('demo') && !usingMocks && door !== 'choose' && <DemoBar />}
      {door === 'centre' ? (
        <AacApp workerId={params.get('worker') ?? 'aac-siti'} />
      ) : door === 'family' ? (
        <FamilyApp contactId={params.get('contact') ?? 'tan-weiling'} />
      ) : (
        <RoleChooser />
      )}
      <footer className="care-footer">
        {usingMocks ? 'Offline demo data. ' : ''}All people in CareLoop's demo are synthetic. No real patient data.
      </footer>
    </main>
  );
}

type Route =
  | { name: 'today' }
  | { name: 'health' }
  | { name: 'activities' }
  | { name: 'plan' }
  | { name: 'settings' }
  | { name: 'handover'; id: string };

function parseRoute(): Route {
  const parts = window.location.pathname.replace(/^\/care(\/family)?\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'handover' && parts[1]) return { name: 'handover', id: parts[1] };
  if (parts[0] === 'pair' || parts[0] === 'settings') return { name: 'settings' };
  if (parts[0] === 'health') return { name: 'health' };
  if (parts[0] === 'activities') return { name: 'activities' };
  if (parts[0] === 'plan') return { name: 'plan' };
  if (parts[0] === 'you') return { name: 'settings' };
  return { name: 'today' };
}

function FamilyApp({ contactId }: { contactId: string }) {
  const route = useRoute(parseRoute);
  const [view, setView] = useState<FamilyView | null>(null);
  const [log, setLog] = useState<LogDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setSeenTick] = useState(0);

  const load = useCallback(() => {
    getFamilyView(contactId).then(
      (v) => {
        setView(v);
        setError(null);
        getLog(v.senior.id, 14, v.contact.id).then(setLog, () => setLog(null));
      },
      (e: Error) => setError(e.message),
    );
  }, [contactId]);
  useLive(load);
  useAlert(
    view?.status === 'red_flag' ? `Red flag: ${view.senior.name}` : view?.status === 'handover' ? `${view.senior.name} needs you` : null,
    view?.red_flags[0]?.text ?? 'Open CareLoop to see the evidence.',
  );

  const onClaimed = (h: Handover) =>
    setView((v) => v && { ...v, handovers: v.handovers.map((x) => (x.id === h.id ? { ...x, ...h } : x)) });

  if (error && !view) return <section className="care-card" role="alert"><h1>We couldn't load this family</h1><p className="care-error">{error}</p><button className="care-secondary" onClick={load}>Try again</button><a className="care-link" href="/care">Choose a demo family</a></section>;
  if (!view) return <p className="care-muted" role="status">Loading your family’s care…</p>;

  // A red flag goes full screen until someone claims its handover. If the engine raised the flag without a
  // red-flag handover, it shows the message until this person says they've seen it.
  const rfHandover = view.handovers.find((h) => h.kind === 'red_flag' && h.status === 'open') ?? null;
  const rfClaimed = view.handovers.some((h) => h.kind === 'red_flag' && h.status !== 'open');
  const latest = [...view.red_flags].sort((a, b) => b.time.localeCompare(a.time));
  const rfMessage = latest.find((m) => m.contact_id === view.contact.id) ?? latest[0] ?? null;
  const showRed = rfHandover || (view.status === 'red_flag' && rfMessage && !rfClaimed && !seenRedFlags().has(rfMessage.id));
  if (showRed) {
    return (
      <RedFlag
        senior={view.senior}
        contactId={view.contact.id}
        aac={false}
        handover={rfHandover}
        message={rfMessage}
        onClaimed={(h) => {
          onClaimed(h);
          load();
        }}
        onSeen={() => {
          if (rfMessage) markRedFlagSeen(rfMessage.id);
          setSeenTick((n) => n + 1);
        }}
      />
    );
  }

  const others = view.other_contacts.map((c) => c.name);
  const openCount = view.handovers.filter((h) => h.status === 'open').length;

  return (
    <div className="fam">
      <header className="family-masthead"><Brand /><span className="family-space">FAMILY SPACE</span><a className="family-profile" href="/care" aria-label="Switch demo family"><span className="family-avatar" aria-hidden="true">{view.contact.name.charAt(0)}</span><span>{view.contact.name}<small>Switch family ↗</small></span></a></header>
      <div className="family-content">
      {error && <p className="care-error">Showing the last update. {error}</p>}
      {route.name === 'handover' ? (
        <HandoverView
          handover={view.handovers.find((x) => x.id === route.id)}
          senior={view.senior}
          contactId={view.contact.id}
          claimerName={(id) => view.other_contacts.find((c) => c.id === id)?.name ?? null}
          others={others}
          fromName={view.contact.name}
          log={log}
          backPath="/care/family"
          onClaimed={onClaimed}
        />
      ) : route.name === 'settings' ? (
        <>
          <TabHeader title="You" senior={view.contact.name} />
          <LookingAfterYou />
          <TextSizeCard />
          <Pairing view={view} />
        </>
      ) : route.name === 'plan' ? (
        <>
          <TabHeader title="Care plan" senior={view.senior.name} />
          <CarePlan seniorId={view.senior.id} contactId={view.contact.id} me={view.contact.name} name={view.senior.name} today={view.today} />
        </>
      ) : route.name === 'health' ? (
        <>
          <TabHeader title="Health" senior={view.senior.name} />
          <Health seniorId={view.senior.id} contactId={view.contact.id} name={view.senior.name} />
        </>
      ) : route.name === 'activities' ? (
        <>
          <TabHeader title="Things to do" senior={view.senior.name} />
          <ActivitiesView seniorId={view.senior.id} contactId={view.contact.id} name={view.senior.name} />
        </>
      ) : (
        <FamilyHome view={view} log={log} />
      )}
      </div>
      <TabBar active={route.name} badge={openCount} />
    </div>
  );
}

const TEXT_KEY = 'careloop-large-text';
function largeText(): boolean {
  try {
    return localStorage.getItem(TEXT_KEY) === '1';
  } catch {
    return false;
  }
}

function TextSizeCard() {
  const [on, setOn] = useState(largeText);
  const toggle = () => {
    const next = !on;
    try {
      localStorage.setItem(TEXT_KEY, next ? '1' : '0');
    } catch {
      /* this page only */
    }
    document.querySelector('main.care')?.classList.toggle('is-large-text', next);
    setOn(next);
  };
  return (
    <section className="care-card">
      <div className="card-head">
        <h2>Bigger text</h2>
        <button role="switch" aria-checked={on} aria-label="Bigger text" className={`switch ${on ? 'is-on' : ''}`} onClick={toggle} />
      </div>
      <p className="care-muted">Makes everything in the app larger on this device.</p>
    </section>
  );
}

function TabHeader({ title, senior }: { title: string; senior: string }) {
  return (
    <header className="tab-header">
      <p className="care-eyebrow">{senior}</p>
      <h1>{title}</h1>
    </header>
  );
}

const TABS = [
  { id: 'today', label: 'Today', path: '/care/family', icon: 'M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z' },
  { id: 'health', label: 'Health', path: '/care/family/health', icon: 'M3 12h4l2-5 4 10 2-5h6' },
  { id: 'plan', label: 'Plan', path: '/care/family/plan', icon: 'M8 3v3M16 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM8 13l2 2 4-4' },
  { id: 'activities', label: 'Activities', path: '/care/family/activities', icon: 'M12 21s-7-5.6-7-11a7 7 0 0 1 14 0c0 5.4-7 11-7 11zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z' },
  { id: 'settings', label: 'You', path: '/care/family/you', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0' },
] as const;

function TabBar({ active, badge }: { active: Route['name']; badge: number }) {
  const current = active === 'handover' ? 'today' : active;
  return (
    <nav className="tabbar" aria-label="Family app">
      {TABS.map((t) => (
        <button key={t.id} className={`tab ${current === t.id ? 'is-active' : ''}`} aria-current={current === t.id ? 'page' : undefined} onClick={() => navigate(t.path)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d={t.icon} />
          </svg>
          <span>{t.label}</span>
          {t.id === 'today' && badge > 0 && <span className="tab-badge" aria-label={`${badge} to act on`}>{badge}</span>}
        </button>
      ))}
    </nav>
  );
}

function DemoBar() {
  const [busy, setBusy] = useState(false);
  const [today, setToday] = useState<string | null>(null);
  const run = async (f: () => Promise<{ today: string }>) => {
    setBusy(true);
    try {
      setToday((await f()).today);
      window.dispatchEvent(new Event(REFRESH_EVENT));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="demo-bar" role="group" aria-label="Demo controls">
      <span>Demo{today ? ` · ${new Date(today).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' })}` : ''}</span>
      <button disabled={busy} onClick={() => run(() => demoAdvance(1))}>
        +1 day
      </button>
      <button disabled={busy} onClick={() => run(() => demoAdvance(11))}>
        +11 days
      </button>
      <button disabled={busy} onClick={() => run(demoReset)}>
        Reset
      </button>
    </div>
  );
}
