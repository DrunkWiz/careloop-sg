// Every day CareLoop decided something, including the days it decided to do nothing. One dot per day,
// oldest on the left; tap a day for what happened and why. `compact` is the 7-dot strip on caseload rows.
import { useState } from 'react';
import type { LogDay } from '../shared/contract';
import { TONE_LABEL, cap, contextNotes, ruleText, toneOf } from './plain';

const fmtDay = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });
const fmtShort = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric' });
const fmtTime = (d: string) => new Date(d).toLocaleTimeString('en-SG', { hour: 'numeric', minute: '2-digit' });

export function TimelineStrip({ log }: { log: LogDay[] }) {
  const days = [...log].reverse();
  return (
    <span className="tl-strip" aria-label={`Last ${days.length} days`}>
      {days.map((d) => (
        <span key={d.date} className={`tl-dot is-${toneOf(d.rung)}`} title={`${fmtDay(d.date)}: ${TONE_LABEL[toneOf(d.rung)]}`} />
      ))}
    </span>
  );
}

export default function Timeline({ log, name }: { log: LogDay[]; name: string }) {
  const days = [...log].reverse();
  const [sel, setSel] = useState<string>(log[0]?.date);
  const day = log.find((d) => d.date === sel) ?? log[0];
  if (!day) return null;

  const counts = log.reduce<Record<string, number>>((acc, d) => {
    const t = toneOf(d.rung);
    acc[t] = (acc[t] ?? 0) + 1;
    return acc;
  }, {});
  const summary = [
    counts.quiet && `${counts.quiet} quiet`,
    counts.nudge && `${counts.nudge} gentle nudge${counts.nudge > 1 ? 's' : ''}`,
    counts.note && `${counts.note} noted`,
    counts.handover && `${counts.handover} handed to you`,
    counts.red && `${counts.red} red flag${counts.red > 1 ? 's' : ''}`,
  ].filter(Boolean);
  const notes = contextNotes(day);

  return (
    <section className="care-card tl">
      <h2>What CareLoop did, day by day</h2>
      <p className="care-muted">
        {summary.join(' · ')}. CareLoop logs every day, including the days it decides to do nothing.
      </p>
      <div className="tl-days" role="listbox" aria-label="Days">
        {days.map((d) => (
          <button
            key={d.date}
            role="option"
            aria-selected={d.date === day.date}
            className={`tl-day ${d.date === day.date ? 'is-selected' : ''}`}
            onClick={() => setSel(d.date)}
            aria-label={`${fmtDay(d.date)}: ${TONE_LABEL[toneOf(d.rung)]}`}
          >
            <span className={`tl-dot is-${toneOf(d.rung)}`} />
            <span className="tl-date">{fmtShort(d.date)}</span>
          </button>
        ))}
      </div>
      <div className="tl-legend" aria-hidden="true">
        {(['quiet', 'nudge', 'note', 'handover', 'red'] as const).map((t) => (
          <span key={t}>
            <span className={`tl-dot is-${t}`} /> {TONE_LABEL[t]}
          </span>
        ))}
      </div>

      <div className={`tl-detail is-${toneOf(day.rung)}`} aria-live="polite">
        <p className="tl-detail-head">
          <strong>{fmtDay(day.date)}</strong>
          <span className={`tl-chip is-${toneOf(day.rung)}`}>{TONE_LABEL[toneOf(day.rung)]}</span>
        </p>
        <p className="tl-detail-line">{ruleText(day.rule_id, day.rung)}</p>
        {day.checkins.map((c, i) => (
          <p key={i} className="tl-said">
            “{c.raw_text}” <span className="care-muted">· {name}, {fmtTime(c.time)}</span>
          </p>
        ))}
        {day.replied === false && <p className="tl-said is-none">No reply to the check-in.</p>}
        <ul className="tl-facts">
          {day.pills && <li>Pills: {day.pills}</li>}
          {day.bp && (
            <li>
              BP: {day.bp.systolic}/{day.bp.diastolic}
            </li>
          )}
          {notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        {day.reason && (
          <details className="tl-engine">
            <summary>The rule's own words</summary>
            <p>
              {cap(day.reason)}. <span className="care-muted">Rule {day.rule_id}.</span>
            </p>
          </details>
        )}
      </div>
    </section>
  );
}
