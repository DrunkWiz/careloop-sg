// The AAC view of /care: for seniors with no family to call.
// Routes: /care/aac · /care/aac/senior/{id} · /care/aac/handover/{id} · /care/aac/programmes
import { useCallback, useEffect, useState } from 'react';
import type { Caseload, CaseloadRow, Handover, LogDay } from '../shared/contract';
import { getBrief, getCaseload, getLog } from '../shared/api';
import HandoverView, { BackLink, KIND_TITLE } from './HandoverView';
import RedFlag from './RedFlag';
import AacSenior from './AacSenior';
import { TimelineStrip } from './Timeline';
import { plainSummary, ruleText } from './plain';
import AacProgrammes from './AacProgrammes';
import { markRedFlagSeen, seenRedFlags, useAlert, useLive, useRoute } from './live';
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
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// The caseload doesn't say which centre the worker belongs to, so read it off a senior's brief.
function useCentre(seniorId: string | undefined) {
  const [centre, setCentre] = useState<{ id: string; name: string } | null>(null);
  useEffect(() => {
    if (!seniorId) return;
    getBrief(seniorId).then(
      (b) => b.aac && setCentre({ id: b.aac.id, name: b.aac.name ?? b.aac.id }),
      () => setCentre(null),
    );
  }, [seniorId]);
  return centre;
}

export default function AacApp({ workerId }: { workerId: string }) {
  const route = useRoute(parseRoute);
  const [data, setData] = useState<Caseload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setSeenTick] = useState(0);
  const [logs, setLogs] = useState<Record<string, LogDay[]>>({});

  const load = useCallback(() => {
    getCaseload(workerId).then(
      (d) => {
        setData(d);
        setError(null);
        // The 7-day strip on each row. One small request per senior; a caseload is tens, not thousands.
        Promise.all(d.seniors.map((r) => getLog(r.senior.id, 7, r.contact_id).then((l) => [r.senior.id, l] as const, () => [r.senior.id, null] as const))).then(
          (pairs) => setLogs(Object.fromEntries(pairs.filter((p): p is readonly [string, LogDay[]] => !!p[1]))),
        );
      },
      (e: Error) => setError(e.message),
    );
  }, [workerId]);
  useLive(load);
  const centre = useCentre(data?.seniors[0]?.senior.id);
  const redRow = data?.seniors.find((r) => r.status === 'red_flag');
  const needCount = data?.seniors.filter((r) => r.status !== 'quiet').length ?? 0;
  useAlert(redRow ? `Red flag: ${redRow.senior.name}` : needCount ? `${needCount} to look at today` : null, redRow?.today.reason ?? 'Open the caseload.');

  if (error && !data) return <p className="care-error">Could not load: {error}</p>;
  if (!data) return <p className="care-muted">Loading…</p>;

  const onClaimed = (h: Handover) =>
    setData((d) => d && { ...d, seniors: d.seniors.map((r) => (r.handover?.id === h.id ? { ...r, handover: { ...r.handover, ...h } } : r)) });

  // A red flag goes full screen until it is claimed (or seen, if the engine raised it without a handover).
  const red = data.seniors.find(
    (r) =>
      r.status === 'red_flag' &&
      (r.handover?.kind === 'red_flag' ? r.handover.status === 'open' : !seenRedFlags().has(`${r.senior.id}-${data.today}`)),
  );
  if (red) {
    const ho = red.handover?.kind === 'red_flag' ? red.handover : null;
    return (
      <RedFlag
        senior={red.senior}
        contactId={red.contact_id}
        aac
        handover={ho}
        message={null}
        reason={red.today.reason}
        onClaimed={(h) => {
          // The caseload only returns open handovers, so remember this one was dealt with.
          markRedFlagSeen(`${red.senior.id}-${data.today}`);
          onClaimed(h);
          load();
        }}
        onSeen={() => {
          markRedFlagSeen(`${red.senior.id}-${data.today}`);
          setSeenTick((n) => n + 1);
        }}
      />
    );
  }

  if (route.name === 'handover') {
    const row = data.seniors.find((r) => r.handover?.id === route.id);
    if (!row) return <NotFound />;
    return (
      <HandoverView
        handover={row.handover ?? undefined}
        senior={row.senior}
        contactId={row.contact_id}
        others={[]}
        fromName={`${centre?.name ?? 'Active Ageing Centre'} staff`}
        log={logs[row.senior.id] ?? null}
        backPath={`/care/aac/senior/${row.senior.id}`}
        onClaimed={onClaimed}
      />
    );
  }

  if (route.name === 'senior') {
    const row = data.seniors.find((r) => r.senior.id === route.id);
    return row ? <AacSenior row={row} /> : <NotFound />;
  }

  if (route.name === 'programmes') {
    return centre ? <AacProgrammes centre={centre} /> : <p className="care-muted">Finding your centre…</p>;
  }

  const needs = data.seniors.filter((r) => r.status !== 'quiet');
  const quiet = data.seniors.filter((r) => r.status === 'quiet');
  const noted = quiet.filter((r) => r.today.rung === '3').length;

  return (
    <>
      {error && <p className="care-error">Showing the last update. {error}</p>}
      <header className="care-header">
        <div>
          <p className="care-eyebrow">{centre?.name ?? 'Your centre'}</p>
          <h1>Caseload</h1>
        </div>
        <button className="care-link" onClick={() => navigate('/care/aac/programmes')} disabled={!centre}>
          Programmes
        </button>
      </header>

      <section className={`care-status ${needs.length ? 'is-action' : 'is-quiet'}`}>
        <p className="care-status-line">
          {needs.length ? `${needs.length} to look at today` : 'Nobody needs a look today'} · {quiet.length} quiet
        </p>
        <p className="care-muted">
          {fmtDay(data.today)}.{noted ? ` ${noted} quiet row${noted === 1 ? '' : 's'} with a note, no alert.` : ''} At most
          one non-urgent alert per senior per week.
        </p>
      </section>

      {needs.length > 0 && (
        <ul className="aac-rows">
          {needs.map((r) => (
            <CaseRow key={r.senior.id} row={r} log={logs[r.senior.id]} />
          ))}
        </ul>
      )}

      <h2 className="aac-section">Quiet</h2>
      <ul className="aac-rows aac-rows-quiet">
        {quiet.map((r) => (
          <CaseRow key={r.senior.id} row={r} log={logs[r.senior.id]} />
        ))}
      </ul>
    </>
  );
}

function rowLine(r: CaseloadRow, log?: LogDay[]): string {
  if (r.handover) return plainSummary(r.handover, r.senior.name);
  const today = log?.find((d) => d.date === log[0]?.date && d.rule_id);
  if (today?.rule_id) return ruleText(today.rule_id, today.rung);
  if (r.today.reason) return cap(r.today.reason.replace(/^no action, because /, '')) + '.';
  return r.last_reply ? `Last replied ${fmtDay(r.last_reply)}.` : 'No check-ins yet.';
}

function CaseRow({ row, log }: { row: CaseloadRow; log?: LogDay[] }) {
  const h = row.handover;
  const chip = row.status === 'red_flag' ? 'Red flag' : h ? KIND_TITLE[h.kind] : row.today.rung === '3' ? 'Noted' : null;
  const cls = row.status === 'quiet' && row.today.rung === '3' ? 'note' : row.status;
  return (
    <li>
      <button className={`aac-row is-${cls}`} onClick={() => navigate(`/care/aac/senior/${row.senior.id}`)}>
        <span className="aac-row-top">
          <strong>{row.senior.name}</strong>
          {chip && <span className={`aac-chip is-${cls}`}>{chip}</span>}
        </span>
        <span className="aac-row-line">{rowLine(row, log)}</span>
        {log && <TimelineStrip log={log} />}
        {h && h.status !== 'open' && <span className="care-pill">You are handling it</span>}
      </button>
    </li>
  );
}

function NotFound() {
  return (
    <>
      <BackLink to="/care/aac" label="Caseload" />
      <p className="care-muted">Not found in this caseload.</p>
    </>
  );
}
