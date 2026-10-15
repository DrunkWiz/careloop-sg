// CareLoop for Centres: the AAC staff console, for seniors with no family to call.
// A work tool, not the family app: many seniors, dense, sortable, desktop-friendly (cards on a phone).
// Routes: /care/aac · /care/aac/senior/{id} · /care/aac/handover/{id} · /care/aac/programmes
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Caseload, CaseloadRow, Finding, Handover, Insights, LogDay } from '../shared/contract';
import { getBrief, getCaseload, getInsights, getLog } from '../shared/api';
import HandoverView, { BackLink, KIND_TITLE } from './HandoverView';
import RedFlag from './RedFlag';
import AacSenior from './AacSenior';
import { TimelineStrip } from './Timeline';
import { plainSummary, ruleText } from './plain';
import AacProgrammes from './AacProgrammes';
import CentreReport from './CentreReport';
import VentSpace from './VentSpace';
import { initials } from './FamilyHome';
import { markRedFlagSeen, seenRedFlags, useAlert, useLive, useRoute } from './live';
import { navigate } from './nav';

type Route =
  | { name: 'caseload' }
  | { name: 'senior'; id: string }
  | { name: 'handover'; id: string }
  | { name: 'programmes' }
  | { name: 'vent' }
  | { name: 'report' };

function parseRoute(): Route {
  const parts = window.location.pathname.replace(/^\/care\/aac\/?/, '').split('/').filter(Boolean);
  if (parts[0] === 'senior' && parts[1]) return { name: 'senior', id: parts[1] };
  if (parts[0] === 'handover' && parts[1]) return { name: 'handover', id: parts[1] };
  if (parts[0] === 'programmes') return { name: 'programmes' };
  if (parts[0] === 'vent') return { name: 'vent' };
  if (parts[0] === 'report') return { name: 'report' };
  return { name: 'caseload' };
}

const fmtDay = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });
const fmtAgo = (d: string, today: string) => {
  const days = Math.round((new Date(today).getTime() - new Date(d.slice(0, 10)).getTime()) / 86400000);
  return days <= 0 ? 'today' : days === 1 ? 'yesterday' : `${days} days ago`;
};

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

export interface SeniorExtras {
  log?: LogDay[];
  insights?: Insights;
}

export default function AacApp({ workerId }: { workerId: string }) {
  const route = useRoute(parseRoute);
  const [data, setData] = useState<Caseload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setSeenTick] = useState(0);
  const [extras, setExtras] = useState<Record<string, SeniorExtras>>({});

  const load = useCallback(() => {
    getCaseload(workerId).then(
      (d) => {
        setData(d);
        setError(null);
        // Per senior: the 7-day strip and what CareLoop noticed. A caseload is tens of seniors, not thousands.
        Promise.all(
          d.seniors.map(async (r) => {
            const [log, insights] = await Promise.all([
              getLog(r.senior.id, 7, r.contact_id).catch(() => null),
              getInsights(r.senior.id, r.contact_id).catch(() => null),
            ]);
            return [r.senior.id, { log: log ?? undefined, insights: insights ?? undefined }] as const;
          }),
        ).then((pairs) => setExtras(Object.fromEntries(pairs)));
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

  let body;
  if (route.name === 'handover') {
    const row = data.seniors.find((r) => r.handover?.id === route.id);
    body = !row ? (
      <NotFound />
    ) : (
      <div className="console-narrow">
        <HandoverView
          handover={row.handover ?? undefined}
          senior={row.senior}
          contactId={row.contact_id}
          others={[]}
          fromName={`${centre?.name ?? 'Active Ageing Centre'} staff`}
          log={extras[row.senior.id]?.log ?? null}
          backPath={`/care/aac/senior/${row.senior.id}`}
          onClaimed={onClaimed}
        />
      </div>
    );
  } else if (route.name === 'senior') {
    const row = data.seniors.find((r) => r.senior.id === route.id);
    body = row ? <AacSenior row={row} insights={extras[row.senior.id]?.insights} today={data.today} /> : <NotFound />;
  } else if (route.name === 'report') {
    body = <CentreReport data={data} extras={extras} centre={centre?.name ?? 'Your centre'} />;
  } else if (route.name === 'programmes') {
    body = centre ? <AacProgrammes centre={centre} seniors={data.seniors} /> : <p className="care-muted">Finding your centre…</p>;
  } else if (route.name === 'vent') {
    body = <div className="console-narrow"><VentSpace compact /></div>;
  } else {
    body = <CaseloadView data={data} extras={extras} />;
  }

  return (
    <div className="console">
      <header className="console-bar">
        <div className="console-brand">
          <span className="console-logo" aria-hidden="true">CL</span>
          <div>
            <strong>CareLoop for Centres</strong>
            <span>{centre?.name ?? 'Your centre'}</span>
          </div>
        </div>
        <nav className="console-nav" aria-label="Centre console">
          <button className={route.name === 'caseload' ? 'is-active' : ''} onClick={() => navigate('/care/aac')}>
            Caseload
          </button>
          <button className={route.name === 'report' ? 'is-active' : ''} onClick={() => navigate('/care/aac/report')}>
            Report
          </button>
          <button className={route.name === 'programmes' ? 'is-active' : ''} onClick={() => navigate('/care/aac/programmes')} disabled={!centre}>
            Programmes
          </button>
          <button className={route.name === 'vent' ? 'is-active' : ''} onClick={() => navigate('/care/aac/vent')}>
            Vent space
          </button>
        </nav>
        <span className="console-user">{workerId === 'aac-siti' ? 'Siti' : workerId}</span>
      </header>
      {error && <p className="care-error">Showing the last update. {error}</p>}
      <div className="console-body">{body}</div>
    </div>
  );
}

type Filter = 'all' | 'look' | 'watch' | 'quiet';

function topWatch(x?: SeniorExtras): Finding | undefined {
  return x?.insights?.findings.find((f) => f.tone === 'watch');
}

function CaseloadView({ data, extras }: { data: Caseload; extras: Record<string, SeniorExtras> }) {
  const [filter, setFilter] = useState<Filter>('all');
  const [q, setQ] = useState('');
  const rows = data.seniors;
  const look = rows.filter((r) => r.status !== 'quiet');
  const watching = rows.filter((r) => r.status === 'quiet' && topWatch(extras[r.senior.id]));
  const repliedToday = rows.filter((r) => r.last_reply?.slice(0, 10) === data.today).length;
  const week = rows.flatMap((r) => extras[r.senior.id]?.log ?? []);
  const weekRate = week.length ? Math.round((week.filter((d) => d.replied).length / week.length) * 100) : null;

  const shown = useMemo(
    () =>
      rows.filter((r) => {
        if (q && !r.senior.name.toLowerCase().includes(q.toLowerCase())) return false;
        if (filter === 'look') return r.status !== 'quiet';
        if (filter === 'watch') return r.status === 'quiet' && !!topWatch(extras[r.senior.id]);
        if (filter === 'quiet') return r.status === 'quiet' && !topWatch(extras[r.senior.id]);
        return true;
      }),
    [rows, q, filter, extras],
  );

  return (
    <>
      <div className="console-title">
        <h1>Caseload</h1>
        <p className="care-muted">{fmtDay(data.today)} · sorted by who needs a look · at most one non-urgent alert per senior a week</p>
      </div>

      <div className="tiles">
        <Tile label="Need a look today" value={look.length} tone={look.length ? 'action' : 'quiet'} />
        <Tile label="Worth watching" value={watching.length} hint="quiet, but a pattern" tone={watching.length ? 'watch' : 'quiet'} />
        <Tile label="Replied today" value={`${repliedToday}/${rows.length}`} />
        <Tile label="Check-ins this week" value={weekRate != null ? `${weekRate}%` : '–'} hint="answered" />
      </div>

      <div className="console-filters">
        <div className="chips" role="tablist" aria-label="Filter">
          {(
            [
              ['all', `All ${rows.length}`],
              ['look', `Need a look ${look.length}`],
              ['watch', `Worth watching ${watching.length}`],
              ['quiet', 'Quiet'],
            ] as const
          ).map(([id, label]) => (
            <button key={id} role="tab" aria-selected={filter === id} className={`chip ${filter === id ? 'is-on' : ''}`} onClick={() => setFilter(id)}>
              {label}
            </button>
          ))}
        </div>
        <input className="console-search" type="search" placeholder="Search seniors" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search seniors" />
      </div>

      <div className="ctable" role="table" aria-label="Caseload">
        <div className="ctable-head" role="row">
          <span role="columnheader">Senior</span>
          <span role="columnheader">Status</span>
          <span role="columnheader">Last 7 days</span>
          <span role="columnheader">CareLoop noticed</span>
          <span role="columnheader">Last reply</span>
        </div>
        {shown.map((r) => (
          <CaseRow key={r.senior.id} row={r} x={extras[r.senior.id]} today={data.today} />
        ))}
        {!shown.length && <p className="care-muted ctable-empty">Nobody matches.</p>}
      </div>
    </>
  );
}

function Tile({ label, value, hint, tone }: { label: string; value: number | string; hint?: string; tone?: 'action' | 'watch' | 'quiet' }) {
  return (
    <div className={`tile ${tone ? `is-${tone}` : ''}`}>
      <span className="tile-value">{value}</span>
      <span className="tile-label">{label}</span>
      {hint && <span className="tile-hint">{hint}</span>}
    </div>
  );
}

function CaseRow({ row, x, today }: { row: CaseloadRow; x?: SeniorExtras; today: string }) {
  const h = row.handover;
  const watch = topWatch(x);
  const noted = row.status === 'quiet' && row.today.rung === '3';
  const status =
    row.status === 'red_flag' ? 'Red flag' : h ? KIND_TITLE[h.kind] : noted ? 'Noted' : watch ? 'Worth watching' : 'Quiet';
  const cls = row.status === 'red_flag' ? 'red' : h ? 'handover' : noted ? 'note' : watch ? 'watch' : 'quiet';
  const line = h
    ? plainSummary(h, row.senior.name)
    : x?.log?.[0]?.rule_id
      ? ruleText(x.log[0].rule_id, x.log[0].rung)
      : row.today.reason ?? 'No decision yet today.';
  return (
    <button className={`ctable-row is-${cls}`} role="row" onClick={() => navigate(`/care/aac/senior/${row.senior.id}`)}>
      <span className="ct-senior" role="cell">
        <span className="avatar is-small" aria-hidden="true">{initials(row.senior.name)}</span>
        <span>
          <strong>{row.senior.name}</strong>
          <span className="ct-sub">{row.senior.language === 'zh' ? 'Mandarin' : row.senior.language === 'en-SG' ? 'Singlish' : 'English'}</span>
        </span>
      </span>
      <span role="cell">
        <span className={`status-chip is-${cls}`}>{status}</span>
        {h && h.status !== 'open' && <span className="ct-sub">You're handling it</span>}
      </span>
      <span role="cell">{x?.log ? <TimelineStrip log={x.log} /> : <span className="care-muted">…</span>}</span>
      <span role="cell" className="ct-noticed">
        {watch ? (
          <>
            <strong>▲ {watch.title}</strong>
            <span className="ct-sub">{line}</span>
          </>
        ) : (
          line
        )}
      </span>
      <span role="cell" className="ct-sub">{row.last_reply ? fmtAgo(row.last_reply, today) : 'never'}</span>
    </button>
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
