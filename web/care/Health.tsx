// Health: what CareLoop noticed, and the last 30 days as charts. Shared by the family app and the centre console.
import { useEffect, useState } from 'react';
import type { Insights } from '../shared/contract';
import { ApiError, getInsights } from '../shared/api';
import Findings from './Findings';
import { useRefreshTick } from './live';
import { BpTrend, PillCalendar, StepsBars } from './charts';

const WEEKDAY: Record<string, string> = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' };

export function useInsights(seniorId: string, contactId?: string) {
  const [data, setData] = useState<Insights | null | undefined>(undefined);
  const [error, setError] = useState<{ status: number | null; message: string } | null>(null);
  const tick = useRefreshTick();
  useEffect(() => {
    getInsights(seniorId, contactId).then(setData, (e: Error) => {
      setError({ status: e instanceof ApiError ? e.status : null, message: e.message });
      setData(null);
    });
  }, [seniorId, contactId, tick]);
  return { data, error };
}

export default function Health({ seniorId, contactId, name }: { seniorId: string; contactId?: string; name: string }) {
  const { data, error } = useInsights(seniorId, contactId);
  if (data === undefined) return <p className="care-muted">Working out the last 30 days…</p>;
  if (!data) {
    return (
      <section className="care-card">
        <h2>Health</h2>
        <p className="care-muted">
          {error?.status === 403 ? `${name} shares only red flags, so there's nothing more to show here.` : `Couldn't load this. ${error?.message ?? ''}`}
        </p>
      </section>
    );
  }
  const { bp, adherence, activity, checkins } = data;
  const missedDays = adherence.by_weekday.filter((w) => w.missed);

  return (
    <>
      <section className="care-section">
        <h2 className="care-section-title">What CareLoop noticed</h2>
        <Findings findings={data.findings} note={data.note} />
      </section>

      <section className="care-card">
        <div className="card-head">
          <h2>Blood pressure, last {data.period.days} days</h2>
          <span className={`trend-pill is-${bp.trend}`}>
            {bp.trend === 'rising' ? '↗ Rising' : bp.trend === 'falling' ? '↘ Falling' : bp.trend === 'steady' ? '→ Steady' : 'Not enough data'}
          </span>
        </div>
        {bp.shared && bp.baseline && bp.series.some((p) => p.systolic != null) ? (
          <>
            <div className="stat-row">
              <Stat label="This week" value={bp.last7_systolic != null ? `${Math.round(bp.last7_systolic)}` : '–'} unit="top, avg" />
              <Stat label="Last week" value={bp.prev7_systolic != null ? `${Math.round(bp.prev7_systolic)}` : '–'} unit="top, avg" />
              <Stat label="Their usual" value={`${Math.round(bp.baseline.systolic)}/${Math.round(bp.baseline.diastolic)}`} unit={bp.baseline.fallback ? 'fallback' : 'learned'} />
              <Stat label="Over 140" value={`${bp.days_over_140 ?? 0}`} unit={`of ${bp.readings_days} days`} />
            </div>
            <BpTrend series={bp.series} baseline={bp.baseline} />
          </>
        ) : (
          <p className="care-muted">{name} shares the digest but not the numbers, so only the direction is shown.</p>
        )}
      </section>

      <section className="care-card">
        <div className="card-head">
          <h2>Medicine</h2>
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

      {activity && (
        <section className="care-card">
          <h2>Moving and seeing people</h2>
          <div className="stat-row">
            <Stat label="Steps, this week" value={activity.steps_last7_avg != null ? activity.steps_last7_avg.toLocaleString() : '–'} unit="a day" />
            <Stat label="Their usual" value={activity.steps_baseline != null ? activity.steps_baseline.toLocaleString() : '–'} unit="a day" />
            <Stat label="Social days" value={`${activity.social_days_last7}`} unit={`this week (last: ${activity.social_days_prev7})`} />
          </div>
          <StepsBars steps={activity.steps} baseline={activity.steps_baseline} />
        </section>
      )}

      <section className="care-card">
        <h2>Check-ins</h2>
        <div className="stat-row">
          <Stat label="Replied" value={`${checkins.replied_days}`} unit={`of ${checkins.days} days`} />
          <Stat label="Usually by" value={checkins.median_first_time ?? '–'} unit={`set for ${checkins.usual_time}`} />
          <Stat label="Rainy days" value={`${data.context.rain_days}`} unit={`haze: ${data.context.haze_days}`} />
        </div>
      </section>
    </>
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
