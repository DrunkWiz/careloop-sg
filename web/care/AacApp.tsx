// The AAC view of /care: for seniors with no family to call.
// Routes: /care/aac · /care/aac/senior/{id} · /care/aac/handover/{id} · /care/aac/programmes
import { useCallback, useEffect, useState } from 'react';
import type { AacCaseload, CaseloadRow, Handover } from '../shared/contract';
import { getCaseload } from '../shared/api';
import HandoverView from './HandoverView';
import RedFlag from './RedFlag';
import AacSenior from './AacSenior';
import AacProgrammes from './AacProgrammes';
import { navigate } from './nav';

type Route =
  | { name: 'caseload' }
  | { name: 'senior'; id: string }
  | { name: 'handover'; id: string }
  | { name: 'programmes' };

function parseRoute(): Route {
  const parts = window.location.pathname.replace(/^\/care\/aac\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'senior' && parts[1]) return { name: 'senior', id: parts[1] };
  if (parts[0] === 'handover' && parts[1]) return { name: 'handover', id: parts[1] };
  if (parts[0] === 'programmes') return { name: 'programmes' };
  return { name: 'caseload' };
}

const fmtDay = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });

export default function AacApp({ contactId }: { contactId: string }) {
  const [route, setRoute] = useState<Route>(parseRoute);
  const [data, setData] = useState<AacCaseload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getCaseload(contactId).then(setData, (e: Error) => setError(e.message));
  }, [contactId]);

  useEffect(load, [load]);
  useEffect(() => {
    const onPop = () => setRoute(parseRoute());
    window.addEventListener('popstate', onPop);
    window.addEventListener('storage', load);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('storage', load);
    };
  }, [load]);

  if (error) return <p className="care-error">Could not load: {error}</p>;
  if (!data) return <p className="care-muted">Loading…</p>;

  const onClaimed = (h: Handover) =>
    setData((d) => d && { ...d, rows: d.rows.map((r) => (r.handover?.id === h.id ? { ...r, handover: h } : r)) });

  const redRow = data.rows.find((r) => r.handover?.kind === 'red_flag' && !r.handover.claimed_by);
  if (redRow?.handover) {
    return <RedFlag senior={redRow.senior} contact={data.contact} handover={redRow.handover} onClaimed={onClaimed} />;
  }

  if (route.name === 'handover') {
    const row = data.rows.find((r) => r.handover?.id === route.id);
    if (!row) return <HandoverMissing />;
    return (
      <HandoverView
        handover={row.handover ?? undefined}
        senior={row.senior}
        contact={data.contact}
        others={data.colleagues.map((c) => c.name)}
        showNumbers={row.senior.consent.family_sees === 'readings'}
        backPath={`/care/aac/senior/${row.senior.id}`}
        onClaimed={onClaimed}
      />
    );
  }

  if (route.name === 'senior') {
    const row = data.rows.find((r) => r.senior.id === route.id);
    return row ? <AacSenior row={row} contact={data.contact} /> : <HandoverMissing />;
  }

  if (route.name === 'programmes') {
    return <AacProgrammes contact={data.contact} centre={data.centre.name} initial={data.programmes} />;
  }

  const needs = data.rows.filter((r) => r.status !== 'quiet');
  const quiet = data.rows.filter((r) => r.status === 'quiet');

  return (
    <>
      <header className="care-header">
        <div>
          <p className="care-eyebrow">
            {data.centre.name} · {data.contact.name}
          </p>
          <h1>Caseload</h1>
        </div>
        <button className="care-link" onClick={() => navigate('/care/aac/programmes')}>
          Programmes
        </button>
      </header>

      <section className={`care-status ${needs.some((r) => r.status !== 'note') ? 'is-action' : 'is-quiet'}`}>
        <p className="care-status-line">
          {needs.filter((r) => r.status !== 'note').length} to look at today · {quiet.length} quiet
        </p>
        <p className="care-muted">
          {fmtDay(data.as_of)}. At most one non-urgent alert per senior per week.
        </p>
      </section>

      {needs.length > 0 && (
        <ul className="aac-rows">
          {needs.map((r) => (
            <CaseRow key={r.senior.id} row={r} />
          ))}
        </ul>
      )}

      <h2 className="aac-section">Quiet</h2>
      <ul className="aac-rows aac-rows-quiet">
        {quiet.map((r) => (
          <CaseRow key={r.senior.id} row={r} />
        ))}
      </ul>
    </>
  );
}

const STATUS_LABEL: Record<CaseloadRow['status'], string> = {
  red_flag: 'Red flag',
  handover: 'Needs a next step',
  no_contact: 'No contact',
  note: 'Noted',
  quiet: 'Quiet',
};

function CaseRow({ row }: { row: CaseloadRow }) {
  const claimed = row.handover?.claimed_by_name;
  return (
    <li>
      <button className={`aac-row is-${row.status}`} onClick={() => navigate(`/care/aac/senior/${row.senior.id}`)}>
        <span className="aac-row-top">
          <strong>{row.senior.name}</strong>
          {row.status !== 'quiet' && <span className={`aac-chip is-${row.status}`}>{STATUS_LABEL[row.status]}</span>}
        </span>
        <span className="aac-row-line">{row.line}</span>
        {claimed && <span className="care-pill">{claimed} is handling it</span>}
      </button>
    </li>
  );
}

function HandoverMissing() {
  return (
    <>
      <button className="care-link care-back" onClick={() => navigate('/care/aac')}>
        ← Caseload
      </button>
      <p className="care-muted">Not found in this caseload.</p>
    </>
  );
}
