// Health: what CareLoop noticed, and the last 30 days as charts. Shared by the family app and the centre console.
import { useEffect, useState } from 'react';
import type { Insights } from '../shared/contract';
import { ApiError, getInsights, usingMocks } from '../shared/api';
import Findings from './Findings';
import HealthApps from './HealthApps';
import { useRefreshTick } from './live';
import { BpTrend, PillCalendar, StepsBars } from './charts';

const WEEKDAY: Record<string, string> = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' };

export function useInsights(seniorId: string, contactId?: string, days = 30) {
  const [data, setData] = useState<Insights | null | undefined>(undefined);
  const [error, setError] = useState<{ status: number | null; message: string } | null>(null);
  const tick = useRefreshTick();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => { setData(undefined); }, [seniorId, contactId, days, attempt]);
  useEffect(() => {
    let active = true;
    setError(null);
    getInsights(seniorId, contactId, days).then((value) => { if (active) setData(value); }, (e: Error) => {
      if (!active) return;
      setError({ status: e instanceof ApiError ? e.status : null, message: e.message });
      setData(null);
    });
    return () => { active = false; };
  }, [seniorId, contactId, tick, days, attempt]);
  return { data, error, retry: () => setAttempt((n) => n + 1) };
}

export default function Health({ seniorId, contactId, name }: { seniorId: string; contactId?: string; name: string }) {
  const [days, setDays] = useState(30);
  const [expanded, setExpanded] = useState(false);
  const { data, error, retry } = useInsights(seniorId, contactId, days);
  if (data === undefined) return <section className="care-card" role="status" aria-busy="true"><h2>Putting the picture together</h2><p className="care-muted">Loading the last {days} days…</p></section>;
  if (!data) {
    return (
      <section className="care-card">
        <h2>Health</h2>
        <p className="care-muted">
          {error?.status === 403 ? `${name} shares only red flags, so there's nothing more to show here.` : `Couldn't load this. ${error?.message ?? ''}`}
        </p>
        {error?.status !== 403 && <button className="care-secondary" onClick={retry}>Try again</button>}
      </section>
    );
  }
  const { bp, adherence, activity, checkins } = data;
  const missedDays = adherence.by_weekday.filter((w) => w.missed);
  const findings = [...data.findings].sort((a, b) => Number(b.tone === 'watch') - Number(a.tone === 'watch'));
  const date = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });

  return (
    <div className="health-dashboard">
      <div className="health-toolbar"><p>{date(data.period.from)} – {date(data.period.to)} <span>· A picture of their everyday health</span></p>
        <div className="health-range" role="group" aria-label="Health period">{[14, 30].map((n) => <button key={n} disabled={usingMocks && n !== 30} aria-pressed={days === n} onClick={() => setDays(n)}>{n} days</button>)}</div>
      </div>
      <div className="health-overview">
        <Stat label="Blood pressure" value={bp.shared && bp.last7_systolic != null ? `${Math.round(bp.last7_systolic)}` : bp.trend === 'unclear' ? '—' : bp.trend} unit={bp.shared && bp.last7_systolic != null ? 'systolic · 7-day average, mmHg' : 'numbers not available'} />
        <Stat label="Medicine taken" value={`${adherence.taken_days}/${adherence.reported_days}`} unit="reported days · self-reported" />
        <Stat label="Daily check-ins" value={`${checkins.replied_days}/${checkins.days}`} unit="days with a reply" />
      </div>
      <div className="health-grid">

      <section className="care-card health-bp">
        <div className="card-head">
          <h2>Blood pressure</h2>
          <span className={`trend-pill is-${bp.trend}`}>
            {bp.trend === 'rising' ? '↗ Rising' : bp.trend === 'falling' ? '↘ Falling' : bp.trend === 'steady' ? '→ Steady' : 'Not enough data'}
          </span>
        </div>
        <p className="care-muted">Last {data.period.days} days, compared with {name}'s usual readings.</p>
        {bp.shared && bp.baseline && bp.series.some((p) => p.systolic != null) ? (
          <>
            <div className="stat-row">
              <Stat label="This week" value={bp.last7_systolic != null ? `${Math.round(bp.last7_systolic)}` : '–'} unit="top, avg" />
              <Stat label="Last week" value={bp.prev7_systolic != null ? `${Math.round(bp.prev7_systolic)}` : '–'} unit="top, avg" />
              <Stat label="Their usual" value={`${Math.round(bp.baseline.systolic)}/${Math.round(bp.baseline.diastolic)}`} unit={bp.baseline.fallback ? 'fallback' : 'learned'} />
              <Stat label="Readings" value={`${bp.readings_days}`} unit="days recorded" />
            </div>
            <BpTrend series={bp.series} baseline={bp.baseline} />
          </>
        ) : (
          <p className="care-muted">{!bp.shared ? `${name} shares the digest but not the numbers, so only the direction is shown.` : 'There are not enough readings yet to show a trend. New readings will appear here when recorded.'}</p>
        )}
      </section>

      <section className="care-card health-medicine">
        <div className="card-head">
          <h2>Medicine routine</h2>
          <span className="care-muted">{adherence.streak_days ? `${adherence.streak_days}-day streak` : ''}</span>
        </div>
        <div className="stat-row">
          <Stat label="Taken" value={`${adherence.taken_days}`} unit={`of ${adherence.reported_days} reported days`} />
          <Stat label="Missed" value={`${adherence.missed_days}`} unit="days" />
        </div>
        <PillCalendar calendar={adherence.calendar} />
        {missedDays.length > 0 && (
          <p className="care-muted">
            Misses by weekday: {missedDays.map((w) => `${WEEKDAY[w.day]} ${w.missed}`).join(', ')}.
          </p>
        )}
      </section>

      <section className="care-card health-findings">
        <div className="card-head"><h2>What CareLoop noticed</h2><span className="care-pill">{findings.length} observations</span></div>
        <p className="care-muted">Patterns in {name}'s own routine, with the evidence behind them.</p>
        {findings.length ? <Findings findings={findings} limit={expanded ? undefined : 3} /> : <p className="care-muted">More check-ins will help build a picture.</p>}
        {findings.length > 3 && <button className="care-link" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? 'Show fewer observations ↑' : `See all ${findings.length} observations ↓`}</button>}
        {data.note && <p className="care-muted findings-note">{data.note}</p>}
      </section>

      {activity && (
        <section className="care-card health-activity">
          <h2>Moving and seeing people</h2>
          <div className="stat-row">
            <Stat label="Steps, this week" value={activity.steps_last7_avg != null ? activity.steps_last7_avg.toLocaleString() : '–'} unit="a day" />
            <Stat label="Their usual" value={activity.steps_baseline != null ? activity.steps_baseline.toLocaleString() : '–'} unit="a day" />
            <Stat label="Social days" value={`${activity.social_days_last7}`} unit={`this week (last: ${activity.social_days_prev7})`} />
          </div>
          <StepsBars steps={activity.steps} baseline={activity.steps_baseline} />
        </section>
      )}

      <div className="health-apps">
        <HealthApps seniorId={seniorId} contactId={contactId} name={name} />
      </div>

      <section className="care-card health-checkins">
        <h2>Check-ins</h2>
        <div className="stat-row">
          <Stat label="Replied" value={`${checkins.replied_days}`} unit={`of ${checkins.days} days`} />
          <Stat label="Usually by" value={checkins.median_first_time ?? '–'} unit={`set for ${checkins.usual_time}`} />
          <Stat label="Rainy days" value={`${data.context.rain_days}`} unit={`haze: ${data.context.haze_days}`} />
        </div>
      </section>
      </div>
    </div>
  );
}

export function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {unit && <span className="stat-unit">{unit}</span>}
    </div>
  );
}
