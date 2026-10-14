// Charts for the Health view. One measure per chart (no dual axes), one hue per series, the senior's usual
// as a dashed reference, status colours only for the medicine calendar (always with an icon and a label).
// Each mark has a hover title; each chart has a text summary for screen readers.
import { useState } from 'react';
import type { BpPoint, Insights } from '../shared/contract';

const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });
const fmtLong = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });

// --- BP over the period ---------------------------------------------------------------------

export function BpTrend({ series, baseline }: { series: BpPoint[]; baseline: { systolic: number; diastolic: number } }) {
  const [hover, setHover] = useState<number | null>(null);
  if (!series.length) return <p className="care-muted">No blood pressure readings yet.</p>;
  const W = 340, H = 190, P = { t: 14, r: 46, b: 22, l: 30 };
  const vals = series.flatMap((p) => [p.systolic, p.diastolic]).filter((v): v is number => v != null).concat(baseline.systolic, baseline.diastolic, 140);
  const lo = Math.floor((Math.min(...vals) - 5) / 10) * 10;
  const hi = Math.ceil((Math.max(...vals) + 5) / 10) * 10;
  const step = (W - P.l - P.r) / Math.max(series.length - 1, 1);
  const x = (i: number) => P.l + i * step;
  const y = (v: number) => P.t + ((hi - v) / (hi - lo)) * (H - P.t - P.b);
  const path = (k: 'systolic' | 'diastolic') => {
    let d = '', pen = false;
    series.forEach((p, i) => {
      const v = p[k];
      if (v == null) return void (pen = false);
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    });
    return d;
  };
  const ticks: number[] = [];
  for (let v = lo; v <= hi; v += 20) ticks.push(v);
  const last = [...series].reverse().find((p) => p.systolic != null);
  const li = last ? series.indexOf(last) : -1;
  const h = hover != null ? series[hover] : null;

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Blood pressure, ${series.length} days, against their usual ${baseline.systolic}/${baseline.diastolic}`}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)} className="ch-grid" />
            <text x={P.l - 6} y={y(v) + 3.5} className="ch-tick" textAnchor="end">{v}</text>
          </g>
        ))}
        <line x1={P.l} x2={W - P.r} y1={y(140)} y2={y(140)} className="ch-ref" />
        <text x={W - P.r + 4} y={y(140) + 3.5} className="ch-tick">140</text>
        {(['systolic', 'diastolic'] as const).map((k) => (
          <line key={k} x1={P.l} x2={W - P.r} y1={y(baseline[k])} y2={y(baseline[k])} className="ch-usual" />
        ))}
        <text x={W - P.r + 4} y={y(baseline.systolic) + 3.5} className="ch-label-usual">usual</text>
        <path d={path('systolic')} className="ch-line" />
        <path d={path('diastolic')} className="ch-line is-dia" />
        {series.map((p, i) =>
          p.systolic != null && p.diastolic != null ? (
            <g key={p.date}>
              <circle cx={x(i)} cy={y(p.systolic)} r={hover === i ? 4.5 : 2.6} className="ch-dot" />
              <circle cx={x(i)} cy={y(p.diastolic)} r={hover === i ? 4 : 2.2} className="ch-dot is-dia" />
            </g>
          ) : null,
        )}
        {/* Hit targets wider than the marks: one column per day. */}
        {series.map((p, i) => (
          <rect key={`hit-${p.date}`} tabIndex={0} role="button" aria-label={p.systolic != null ? `${fmtLong(p.date)}: ${p.systolic}/${p.diastolic} mmHg` : `${fmtLong(p.date)}: no reading`} onFocus={() => setHover(i)} onBlur={() => setHover(null)} x={x(i) - step / 2} y={P.t} width={step} height={H - P.t - P.b} fill="transparent"
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onClick={() => setHover(i)}>
            <title>{p.systolic != null ? `${fmtLong(p.date)}: ${p.systolic}/${p.diastolic}` : `${fmtLong(p.date)}: no reading`}</title>
          </rect>
        ))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} className="ch-cross" />}
        {last && (
          <>
            <text x={x(li) + 6} y={y(last.systolic!) + 3.5} className="ch-label">top</text>
            <text x={x(li) + 6} y={y(last.diastolic!) + 3.5} className="ch-label">bottom</text>
          </>
        )}
        <text x={P.l} y={H - 5} className="ch-tick">{fmt(series[0].date)}</text>
        <text x={W - P.r} y={H - 5} className="ch-tick" textAnchor="end">{fmt(series[series.length - 1].date)}</text>
      </svg>
      <figcaption>
        {h ? (
          <strong>{h.systolic != null ? `${fmtLong(h.date)}: ${h.systolic}/${h.diastolic} mmHg` : `${fmtLong(h.date)}: no reading`}</strong>
        ) : (
          <>Tap a day for its reading. Dashed: their usual ({Math.round(baseline.systolic)}/{Math.round(baseline.diastolic)}). Dotted: 140.</>
        )}
      </figcaption>
    </figure>
  );
}

// --- Medicine calendar ----------------------------------------------------------------------

export function PillCalendar({ calendar }: { calendar: Insights['adherence']['calendar'] }) {
  if (!calendar.length) return <p className="care-muted">No medicine reports yet.</p>;
  // Monday-first weeks, so a weekday pattern lines up in a column.
  const first = new Date(calendar[0].date);
  const pad = (first.getDay() + 6) % 7;
  const cells: (typeof calendar[number] | null)[] = [...Array(pad).fill(null), ...calendar];
  const icon = { taken: '✓', missed: '✕' } as const;
  return (
    <figure className="chart">
      <div className="cal" role="img" aria-label={`Medicine over ${calendar.length} days: taken on ${calendar.filter((c) => c.pills === 'taken').length}, missed on ${calendar.filter((c) => c.pills === 'missed').length}`}>
        {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
          <span key={`h${i}`} className="cal-head">{d}</span>
        ))}
        {cells.map((c, i) =>
          c ? (
            <span key={c.date} className={`cal-cell is-${c.pills ?? 'none'}`} title={`${fmtLong(c.date)}: ${c.pills ?? 'not reported'}`}>
              {c.pills ? icon[c.pills] : ''}
            </span>
          ) : (
            <span key={`pad${i}`} />
          ),
        )}
      </div>
      <figcaption className="cal-legend">
        <span><span className="cal-cell is-taken">✓</span> Taken</span>
        <span><span className="cal-cell is-missed">✕</span> Missed</span>
        <span><span className="cal-cell is-none" /> Not reported</span>
      </figcaption>
    </figure>
  );
}

// --- Steps ----------------------------------------------------------------------------------

export function StepsBars({ steps, baseline }: { steps: { date: string; steps: number | null }[]; baseline: number | null }) {
  const [hover, setHover] = useState<number | null>(null);
  if (!steps.length) return <p className="care-muted">No activity reports yet.</p>;
  const W = 340, H = 120, P = { t: 10, r: 46, b: 20, l: 30 };
  const max = Math.max(...steps.map((s) => s.steps ?? 0), baseline ?? 0, 1000);
  const top = Math.ceil(max / 2000) * 2000;
  const bw = (W - P.l - P.r) / steps.length;
  const y = (v: number) => P.t + (1 - v / top) * (H - P.t - P.b);
  const h = hover != null ? steps[hover] : null;
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Daily steps over ${steps.length} days${baseline ? `, usual about ${Math.round(baseline)}` : ''}`}>
        {[0, top / 2, top].map((v) => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)} className="ch-grid" />
            <text x={P.l - 6} y={y(v) + 3.5} className="ch-tick" textAnchor="end">{v >= 1000 ? `${v / 1000}k` : v}</text>
          </g>
        ))}
        {steps.map((s, i) =>
          s.steps != null ? (
            <rect key={s.date} x={P.l + i * bw + 1} y={y(s.steps)} width={Math.max(bw - 2, 1)} height={y(0) - y(s.steps)} rx={2}
              className={`ch-bar ${hover === i ? 'is-hover' : ''}`} />
          ) : null,
        )}
        {baseline != null && (
          <>
            <line x1={P.l} x2={W - P.r} y1={y(baseline)} y2={y(baseline)} className="ch-usual" />
            <text x={W - P.r + 4} y={y(baseline) + 3.5} className="ch-label-usual">usual</text>
          </>
        )}
        {steps.map((s, i) => (
          <rect key={`hit-${s.date}`} x={P.l + i * bw} y={P.t} width={bw} height={H - P.t - P.b} fill="transparent"
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onClick={() => setHover(i)}>
            <title>{`${fmtLong(s.date)}: ${s.steps != null ? s.steps.toLocaleString() + ' steps' : 'no data'}`}</title>
          </rect>
        ))}
        <text x={P.l} y={H - 5} className="ch-tick">{fmt(steps[0].date)}</text>
        <text x={W - P.r} y={H - 5} className="ch-tick" textAnchor="end">{fmt(steps[steps.length - 1].date)}</text>
      </svg>
      <figcaption>
        {h ? <strong>{fmtLong(h.date)}: {h.steps != null ? `${h.steps.toLocaleString()} steps` : 'no data'}</strong> : 'Tap a day for its steps. Synthetic step counts in the demo.'}
      </figcaption>
    </figure>
  );
}
