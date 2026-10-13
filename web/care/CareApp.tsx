// The /care app: family view + AAC view, chosen by the logged-in contact's role. Owner: Nathan.
// Until login exists, the contact comes from ?contact= (default: the first family contact).
import { useCallback, useEffect, useState } from 'react';
import type { FamilyView, Handover } from '../shared/contract';
import { getFamilyView, usingMocks } from '../shared/api';
import FamilyHome from './FamilyHome';
import HandoverView from './HandoverView';
import RedFlag from './RedFlag';
import Pairing from './Pairing';
import './care.css';

type Route = { name: 'home' } | { name: 'handover'; id: string } | { name: 'pair' };

function parseRoute(): Route {
  const parts = window.location.pathname.replace(/^\/care\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'handover' && parts[1]) return { name: 'handover', id: parts[1] };
  if (parts[0] === 'pair') return { name: 'pair' };
  return { name: 'home' };
}

export default function CareApp() {
  const contactId = new URLSearchParams(window.location.search).get('contact') ?? 'c-meiling';
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
    const onStorage = () => load();
    window.addEventListener('popstate', onPop);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('storage', onStorage);
    };
  }, [load]);

  const onClaimed = (h: Handover) =>
    setView((v) => v && { ...v, handovers: v.handovers.map((x) => (x.id === h.id ? h : x)) });

  if (error) return <main className="care"><p className="care-error">Could not load: {error}</p></main>;
  if (!view) return <main className="care"><p className="care-muted">Loading…</p></main>;

  const openRedFlag = view.handovers.find((h) => h.kind === 'red_flag' && !h.claimed_by);

  return (
    <main className="care">
      {openRedFlag ? (
        <RedFlag view={view} handover={openRedFlag} onClaimed={onClaimed} />
      ) : route.name === 'handover' ? (
        <HandoverView view={view} id={route.id} onClaimed={onClaimed} />
      ) : route.name === 'pair' ? (
        <Pairing view={view} />
      ) : (
        <FamilyHome view={view} />
      )}
      {(view.synthetic || usingMocks) && (
        <footer className="care-footer">Synthetic demo data. No real patient data.</footer>
      )}
    </main>
  );
}
