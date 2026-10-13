// The /care app: family view + AAC view, chosen by the logged-in contact's role. Owner: Nathan.
// Until login exists, the view comes from the path (/care vs /care/aac) and the contact from ?contact=.
import { useCallback, useEffect, useState } from 'react';
import type { FamilyView, Handover } from '../shared/contract';
import { getFamilyView, usingMocks } from '../shared/api';
import FamilyHome from './FamilyHome';
import HandoverView from './HandoverView';
import RedFlag from './RedFlag';
import Pairing from './Pairing';
import AacApp from './AacApp';
import './care.css';

export default function CareApp() {
  const aac = window.location.pathname.startsWith('/care/aac');
  const contact = new URLSearchParams(window.location.search).get('contact');

  return (
    <main className="care">
      {aac ? <AacApp contactId={contact ?? 'c-aac-farah'} /> : <FamilyApp contactId={contact ?? 'c-meiling'} />}
      {usingMocks && <footer className="care-footer">Synthetic demo data. No real patient data.</footer>}
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
  const [route, setRoute] = useState<Route>(parseRoute);
  const [view, setView] = useState<FamilyView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getFamilyView(contactId).then(setView, (e: Error) => setError(e.message));
  }, [contactId]);

  useEffect(load, [load]);

  useEffect(() => {
    const onPop = () => setRoute(parseRoute());
    // Another tab (another family member) claiming a handover shows up here too.
    window.addEventListener('popstate', onPop);
    window.addEventListener('storage', load);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('storage', load);
    };
  }, [load]);

  const onClaimed = (h: Handover) =>
    setView((v) => v && { ...v, handovers: v.handovers.map((x) => (x.id === h.id ? h : x)) });

  if (error) return <p className="care-error">Could not load: {error}</p>;
  if (!view) return <p className="care-muted">Loading…</p>;

  const openRedFlag = view.handovers.find((h) => h.kind === 'red_flag' && !h.claimed_by);
  if (openRedFlag) {
    return <RedFlag senior={view.senior} contact={view.contact} handover={openRedFlag} onClaimed={onClaimed} />;
  }

  if (route.name === 'handover') {
    return (
      <HandoverView
        handover={view.handovers.find((x) => x.id === route.id)}
        senior={view.senior}
        contact={view.contact}
        others={view.family.filter((c) => c.id !== view.contact.id).map((c) => c.name)}
        showNumbers={view.senior.consent.family_sees === 'readings'}
        backPath="/care"
        onClaimed={onClaimed}
      />
    );
  }

  if (route.name === 'pair') return <Pairing view={view} />;
  return <FamilyHome view={view} />;
}
