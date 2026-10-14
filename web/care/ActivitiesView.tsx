// Things to do near the senior, pulled in automatically: their own AAC's programmes this week, the nearest
// AACs and community clubs (data.gov.sg), what CareLoop suggested today and how the senior has answered.
// Nothing here is booked: the senior picks, and a "not for me" is remembered.
import { useEffect, useState } from 'react';
import type { Activities } from '../shared/contract';
import { getActivities } from '../shared/api';
import { useRefreshTick } from './live';

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
const DAY_LABEL: Record<string, string> = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' };
const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });
// Programme times come as "2pm", "8:30am" or "14:00". Minutes after midnight, for sorting.
export function timeKey(t: string): number {
  const m = t.trim().toLowerCase().match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
  if (!m) return 24 * 60;
  let h = +m[1] % 12;
  if (m[3] === 'pm') h += 12;
  if (!m[3] && +m[1] >= 12) h = +m[1];
  return h * 60 + (m[2] ? +m[2] : 0);
}

const map = (lat: number, lon: number) => `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;

export function useActivities(seniorId: string, contactId?: string) {
  const [data, setData] = useState<Activities | null | undefined>(undefined);
  const tick = useRefreshTick();
  useEffect(() => {
    getActivities(seniorId, contactId).then(setData, () => setData(null));
  }, [seniorId, contactId, tick]);
  return data;
}

export default function ActivitiesView({ seniorId, contactId, name, compact }: { seniorId: string; contactId?: string; name: string; compact?: boolean }) {
  const a = useActivities(seniorId, contactId);
  if (a === undefined) return <p className="care-muted">Finding things to do nearby…</p>;
  if (!a) return <p className="care-muted">Couldn't load activities.</p>;
  const going = a.suggestions.filter((s) => s.response === 'going').length;
  const notForMe = a.suggestions.filter((s) => s.response === 'not_for_me').length;

  return (
    <>
      {a.indoor_only && (
        <p className="care-notice">
          {a.why_indoor === 'rain' ? `Rain today (${a.rain_mm} mm nearby)` : `Haze today (PSI ${a.psi})`}: CareLoop is only suggesting indoor options.
        </p>
      )}

      <section className="care-card">
        <h2>Suggested to {name} today</h2>
        <p className="care-muted">Picked by CareLoop's rules from what {name} likes{a.likes.length ? ` (${a.likes.join(', ')})` : ''}: their own centre first, then the nearest community club.</p>
        <ul className="act-list">
          {a.suggested_today.map((s, i) => (
            <li key={i} className="act-item">
              <span className={`act-kind is-${s.kind}`}>{s.kind === 'cc' ? 'CC' : s.kind === 'aac' ? 'AAC' : 'Programme'}</span>
              <span className="act-body">
                <strong>{s.place}</strong>
                <span className="care-muted">
                  {s.why_it_fits} · {s.indoor ? 'Indoor' : 'Outdoor'}
                  {s.sample && ' · sample timetable'}
                </span>
              </span>
            </li>
          ))}
        </ul>
        {(going > 0 || notForMe > 0) && (
          <p className="care-muted">Last two weeks: said "going" {going} time{going === 1 ? '' : 's'}, "not for me" {notForMe}. A "not for me" isn't suggested again.</p>
        )}
      </section>

      {a.own_aac && (
        <section className="care-card">
          <h2>This week at {a.own_aac.name}</h2>
          <p className="care-muted">{a.own_aac.address}</p>
          <div className="week">
            {DAYS.map((d) => {
              const items = a.own_aac!.programmes.filter((p) => p.weekdays.includes(d) && !p.hidden).sort((x, y) => timeKey(x.time) - timeKey(y.time));
              return (
                <div key={d} className={`week-day ${d === a.weekday ? 'is-today' : ''}`}>
                  <span className="week-label">{DAY_LABEL[d]}{d === a.weekday ? ' · today' : ''}</span>
                  {items.length ? (
                    items.map((p) => (
                      <span key={p.id} className={`week-prog ${p.fits ? 'is-fit' : ''} ${a.indoor_only && !p.indoor ? 'is-out' : ''}`}>
                        <span className="week-time">{p.time}</span> {p.title}
                        {p.fits && <span className="week-fit">likes {p.fits}</span>}
                      </span>
                    ))
                  ) : (
                    <span className="care-muted week-none">–</span>
                  )}
                </div>
              );
            })}
          </div>
          {a.own_aac.programmes.some((p) => p.sample) && <p className="care-muted">Sample timetable: the centre hasn't entered its own yet.</p>}
        </section>
      )}

      {!compact && (
        <section className="care-card">
          <h2>Nearby</h2>
          <p className="care-muted">Distances from {a.distance_from}, as the crow flies.</p>
          <ul className="act-list">
            {[...a.nearby_ccs, ...a.nearby_aacs]
              .sort((x, y) => x.km - y.km)
              .map((p) => (
                <li key={p.id} className="act-item">
                  <span className={`act-kind is-${p.kind}`}>{p.kind === 'cc' ? 'CC' : 'AAC'}</span>
                  <span className="act-body">
                    <strong>{p.name}</strong>
                    <span className="care-muted">
                      {p.km} km · {p.address}
                    </span>
                  </span>
                  <a className="care-link act-map" href={map(p.lat, p.lon)} target="_blank" rel="noreferrer">
                    Map
                  </a>
                </li>
              ))}
          </ul>
        </section>
      )}

      {!compact && a.suggestions.length > 0 && (
        <section className="care-card">
          <h2>Recent suggestions</h2>
          <ul className="act-list">
            {a.suggestions.slice(0, 8).map((s) => (
              <li key={s.id} className="act-item">
                <span className="act-date">{fmt(s.date)}</span>
                <span className="act-body">
                  <strong>{s.place}</strong>
                  <span className="care-muted">{s.why_it_fits}</span>
                </span>
                <span className={`act-resp is-${s.response ?? 'none'}`}>
                  {s.response === 'going' ? 'Going' : s.response === 'not_for_me' ? 'Not for me' : 'No answer'}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!compact && <p className="care-muted care-source">{a.source}</p>}
    </>
  );
}
