// Small BP chart: systolic and diastolic against the senior's own baseline (dashed).
// Days without a reading are gaps, not zeros. Flagged days (the handover's evidence.dates) are shaded.
import type { BpPoint } from '../shared/contract';

interface Props {
  series: BpPoint[];
  baseline: { systolic: number; diastolic: number };
  flagged?: string[];
}

const W = 340;
const H = 180;
const PAD = { top: 12, right: 44, bottom: 24, left: 30 };

export default function BpChart({ series, baseline, flagged = [] }: Props) {
  const values = series
    .flatMap((p) => [p.systolic, p.diastolic])
    .filter((v): v is number => v != null)
    .concat(baseline.systolic, baseline.diastolic);
  const lo = Math.floor((Math.min(...values) - 5) / 10) * 10;
  const hi = Math.ceil((Math.max(...values) + 5) / 10) * 10;
  const step = (W - PAD.left - PAD.right) / Math.max(series.length - 1, 1);
  const x = (i: number) => PAD.left + i * step;
  const y = (v: number) => PAD.top + ((hi - v) / (hi - lo)) * (H - PAD.top - PAD.bottom);

  // One path per run of consecutive readings, so missing days show as gaps.
  const path = (key: 'systolic' | 'diastolic') => {
    let d = '';
    let pen = false;
    series.forEach((p, i) => {
      const v = p[key];
      if (v == null) {
        pen = false;
        return;
      }
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    });
    return d;
  };
  const ticks: number[] = [];
  for (let v = lo; v <= hi; v += 20) ticks.push(v);
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });
  const last = [...series].reverse().find((p) => p.systolic != null && p.diastolic != null);
  const lastIdx = last ? series.indexOf(last) : -1;
  const flaggedSet = new Set(flagged);

  return (
    <figure className="bp-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Blood pressure over the last 14 days against their usual">
        {series.map((p, i) =>
          flaggedSet.has(p.date) ? (
            <rect key={p.date} x={x(i) - step / 2} y={PAD.top} width={step} height={H - PAD.top - PAD.bottom} className="bp-since" />
          ) : null,
        )}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} className="bp-grid" />
            <text x={PAD.left - 6} y={y(v) + 4} className="bp-tick" textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        <line x1={PAD.left} x2={W - PAD.right} y1={y(baseline.systolic)} y2={y(baseline.systolic)} className="bp-baseline" />
        <line x1={PAD.left} x2={W - PAD.right} y1={y(baseline.diastolic)} y2={y(baseline.diastolic)} className="bp-baseline" />
        <text x={W - PAD.right + 4} y={y(baseline.systolic) + 4} className="bp-label">
          usual
        </text>
        <path d={path('systolic')} className="bp-line" />
        <path d={path('diastolic')} className="bp-line bp-line-dia" />
        {series.map((p, i) =>
          p.systolic != null && p.diastolic != null ? (
            <g key={`d-${p.date}`}>
              <circle cx={x(i)} cy={y(p.systolic)} r={2.5} className="bp-dot" />
              <circle cx={x(i)} cy={y(p.diastolic)} r={2} className="bp-dot bp-dot-dia" />
            </g>
          ) : null,
        )}
        {last && last.systolic != null && last.diastolic != null && (
          <>
            <text x={x(lastIdx) + 6} y={y(last.systolic) + 4} className="bp-label bp-label-strong">
              top
            </text>
            <text x={x(lastIdx) + 6} y={y(last.diastolic) + 4} className="bp-label bp-label-strong">
              bottom
            </text>
          </>
        )}
        <text x={PAD.left} y={H - 6} className="bp-tick">
          {fmt(series[0].date)}
        </text>
        <text x={W - PAD.right} y={H - 6} className="bp-tick" textAnchor="end">
          {fmt(series[series.length - 1].date)}
        </text>
      </svg>
      <figcaption>
        mmHg. Dashed lines are their usual ({Math.round(baseline.systolic)}/{Math.round(baseline.diastolic)}).
        {flagged.length > 0 && ' Shaded: the days CareLoop flagged.'} Gaps: no reading that day.
      </figcaption>
    </figure>
  );
}
