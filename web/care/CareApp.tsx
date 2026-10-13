// The /care app: family view + AAC view. Owner: Nathan.
// Until login exists: /care?contact=<family contact id> is the family view, /care/aac?worker=<worker id> the AAC view.
import { useCallback, useState } from 'react';
import type { FamilyView, Handover, LogDay } from '../shared/contract';
import { demoAdvance, demoReset, getFamilyView, getLog, usingMocks } from '../shared/api';
import FamilyHome from './FamilyHome';
import HandoverView from './HandoverView';
import RedFlag from './RedFlag';
import Pairing from './Pairing';
import AacApp from './AacApp';
import { REFRESH_EVENT, markRedFlagSeen, seenRedFlags, useAlert, useLive, useRoute } from './live';
import './care.css';


export default function CareApp() {
  const params = new URLSearchParams(window.location.search);
  const aac = window.location.pathname.startsWith('/care/aac');

  return (
    <main className="care">
      {aac ? (
        <AacApp workerId={params.get('worker') ?? 'aac-siti'} />
      ) : (
        <FamilyApp contactId={params.get('contact') ?? 'tan-weiling'} />
      )}
      {params.has('demo') && !usingMocks && <DemoBar />}
      <footer className="care-footer">
        {usingMocks ? 'Offline demo data. ' : ''}All people in CareLoop's demo are synthetic. No real patient data.
      </footer>
    </main>
  );
}

type Route = { name: 'home' } | { name: 'handover'; id: string } | { name: 'pair' };

function parseRoute(): Route {
  const parts = window.location.pathname.replace(/^\/care\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'handover' && parts[1]) return { name: 'handover', id: parts[1] };
  if (parts[0] === 'pair') return { name: 'pair' };
  return { name: 'home' };
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

  if (error && !view) return <p className="care-error">Could not load: {error}</p>;
  if (!view) return <p className="care-muted">Loading…</p>;

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

  return (
    <>
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
          backPath="/care"
          onClaimed={onClaimed}
        />
      ) : route.name === 'pair' ? (
        <Pairing view={view} />
      ) : (
        <FamilyHome view={view} log={log} />
      )}
    </>
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
