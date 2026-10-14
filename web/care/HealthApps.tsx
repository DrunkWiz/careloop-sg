// The senior's phone: what syncs from Apple Health or Health Connect (a Fitbit, an OMRON cuff), when it last
// synced, and the last days of it. In the demo there is no CareLoop phone app yet: the "sync now" buttons
// stand in for it, sending what Health Connect or Apple Health would.
import { useCallback, useEffect, useState } from 'react';
import type { HealthSyncResult, HealthSyncView } from '../shared/contract';
import { demoHealthSync, getHealthSync, usingMocks } from '../shared/api';
import { REFRESH_EVENT, useLive } from './live';

const day = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric' });
const when = (d: string) =>
  new Date(d).toLocaleString('en-SG', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
const RUNG: Record<string, string> = {
  '0': 'nothing needed',
  '1': 'a gentle question',
  '2': 'a gentle nudge',
  '3': 'noted',
  '4': 'handed over to a person',
  R: 'a red flag: family or centre told now',
};

export default function HealthApps({ seniorId, contactId, name, compact = false }: { seniorId: string; contactId?: string; name: string; compact?: boolean }) {
  const [v, setV] = useState<HealthSyncView | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<HealthSyncResult | null>(null);
  const [cuff, setCuff] = useState({ s: '', d: '' });

  const load = useCallback(() => {
    getHealthSync(seniorId, contactId).then(setV, (e) => setErr(String(e.message ?? e)));
  }, [seniorId, contactId]);
  useEffect(load, [load]);
  useLive(load);

  const sync = async (bp?: [number, number]) => {
    setBusy(true);
    try {
      const r = await demoHealthSync(seniorId, bp);
      setResult(r);
      setCuff({ s: '', d: '' });
      window.dispatchEvent(new Event(REFRESH_EVENT)); // the rest of the app picks up the new readings
    } catch (e) {
      setErr(String((e as Error).message));
    } finally {
      setBusy(false);
    }
  };

  if (err) return <section className="care-card"><h2>Health apps</h2><p className="care-muted">Couldn't load: {err}</p></section>;
  if (!v) return <section className="care-card"><h2>Health apps</h2><p className="care-muted">Loading…</p></section>;

  if (!v.connected || !v.status) {
    return (
      <section className="care-card hs">
        <h2>Health apps</h2>
        <p className="care-muted">
          {name}'s phone isn't connected, so steps come from the phone's own step counter. A Fitbit or an OMRON cuff can
          send readings on their own, through Apple Health on an iPhone or Health Connect on Android.
        </p>
      </section>
    );
  }

  const st = v.status;
  const cuffConnected = st.apps.includes('OMRON connect');
  const rows = [...v.days].reverse();
  const s = Number(cuff.s), d = Number(cuff.d);
  const cuffOk = s >= 50 && s <= 300 && d >= 30 && d <= 200;

  return (
    <section className="care-card hs">
      <div className="card-head">
        <h2>{compact ? 'Health apps' : `${name}'s health apps`}</h2>
        <span className="care-pill">Synced {when(st.last_sync)}</span>
      </div>
      <ol className="hs-flow" aria-label="Where the data comes from">
        <li>{st.apps.join(' + ') || 'Phone'}<small>{st.apps.length > 1 ? 'each writes to' : 'writes to'}</small></li>
        <li>{st.platform_name}<small>{st.platform === 'healthkit' ? 'iPhone' : 'Android'}</small></li>
        <li>CareLoop</li>
      </ol>
      <p className="care-muted">
        Sends {st.kinds.join(', ')}. Readings come straight from the devices, so {name} doesn't have to type them in.
      </p>

      <div className="hs-table" role="table" aria-label={`Last ${rows.length} days from ${name}'s phone`}>
        <div className="hs-row is-head" role="row">
          <span role="columnheader">Day</span>
          <span role="columnheader">Steps</span>
          <span role="columnheader">Resting HR</span>
          <span role="columnheader">Sleep</span>
          {v.shares_readings && <span role="columnheader">BP (cuff)</span>}
        </div>
        {rows.map((r) => (
          <div className="hs-row" role="row" key={r.date}>
            <span role="cell">{day(r.date)}</span>
            <span role="cell">{r.steps != null ? r.steps.toLocaleString() : '–'}</span>
            <span role="cell">{r.resting_hr != null ? `${r.resting_hr} bpm` : '–'}</span>
            <span role="cell">{r.sleep_hours != null ? `${r.sleep_hours} h` : '–'}</span>
            {v.shares_readings && <span role="cell">{r.bp.length ? r.bp.map((b) => `${b.systolic}/${b.diastolic}`).join(', ') : '–'}</span>}
          </div>
        ))}
      </div>
      {!v.shares_activity && <p className="care-muted">{name} doesn't share activity, so steps and sleep are hidden.</p>}
      {!v.shares_readings && <p className="care-muted">{name} shares a weekly summary, not readings, so BP numbers are hidden.</p>}

      {!usingMocks && (
        <div className="hs-demo">
          <p className="hs-demo-label">Demo: stands in for {name}'s phone</p>
          <div className="hs-demo-actions">
            <button className="care-secondary" disabled={busy} onClick={() => void sync()}>
              {busy ? 'Syncing…' : 'Sync now'}
            </button>
            {cuffConnected && (
              <form
                className="hs-cuff"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (cuffOk) void sync([s, d]);
                }}
              >
                <label>
                  <span>Cuff reading</span>
                  <input inputMode="numeric" aria-label="Top number" placeholder="top" value={cuff.s} onChange={(e) => setCuff({ ...cuff, s: e.target.value })} />
                  <span aria-hidden="true">/</span>
                  <input inputMode="numeric" aria-label="Bottom number" placeholder="bottom" value={cuff.d} onChange={(e) => setCuff({ ...cuff, d: e.target.value })} />
                </label>
                <button className="care-secondary" disabled={busy || !cuffOk}>Measure</button>
              </form>
            )}
          </div>
          {result && (
            <p className={`hs-result ${result.rung === 'R' ? 'is-red' : ''}`} aria-live="polite">
              {Object.keys(result.imported).length
                ? `Synced: ${Object.entries(result.imported)
                    .map(([k, n]) => (k === 'bp' ? `${n} BP reading${n > 1 ? 's' : ''}` : k === 'hr' ? 'resting heart rate' : k))
                    .join(', ')}. `
                : 'Synced: nothing yet today. '}
              {result.skipped ? `${result.skipped} skipped. ` : ''}
              {result.rung ? `CareLoop's decision for today: ${RUNG[result.rung]}.` : ''}
            </p>
          )}
          <p className="care-muted">Simulated: CareLoop has no phone app yet. This sends what {st.platform_name} would, from synthetic Fitbit and OMRON data.</p>
        </div>
      )}
    </section>
  );
}
