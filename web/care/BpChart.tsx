// Small BP chart: systolic and diastolic against the senior's own baseline (dashed).
interface Props {
  series: { date: string; systolic: number; diastolic: number }[];
  baseline: { systolic: number; diastolic: number };
  since?: string;
}

const W = 340;
const H = 180;
const PAD = { top: 12, right: 44, bottom: 24, left: 30 };

export default function BpChart({ series, baseline, since }: Props) {
  const values = series.flatMap((p) => [p.systolic, p.diastolic]).concat(baseline.systolic, baseline.diastolic);
  const lo = Math.floor((Math.min(...values) - 5) / 10) * 10;
  const hi = Math.ceil((Math.max(...values) + 5) / 10) * 10;
  const x = (i: number) => PAD.left + (i / (series.length - 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + ((hi - v) / (hi - lo)) * (H - PAD.top - PAD.bottom);
  const path = (key: 'systolic' | 'diastolic') =>
    series.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ');
  const sinceIdx = since ? series.findIndex((p) => p.date >= since) : -1;
  const ticks = [];
  for (let v = lo; v <= hi; v += 20) ticks.push(v);
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });

  return (
    <figure className="bp-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Blood pressure over the last 14 days against their usual">
        {sinceIdx > 0 && (
          <rect
            x={x(sinceIdx)}
            y={PAD.top}
            width={x(series.length - 1) - x(sinceIdx)}
            height={H - PAD.top - PAD.bottom}
            className="bp-since"
          />
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
        <text x={W - PAD.right + 4} y={y(series[series.length - 1].systolic) + 4} className="bp-label bp-label-strong">
          top
        </text>
        <text x={W - PAD.right + 4} y={y(series[series.length - 1].diastolic) + 4} className="bp-label bp-label-strong">
          bottom
        </text>
        <text x={PAD.left} y={H - 6} className="bp-tick">
          {fmt(series[0].date)}
        </text>
        <text x={W - PAD.right} y={H - 6} className="bp-tick" textAnchor="end">
          {fmt(series[series.length - 1].date)}
        </text>
      </svg>
      <figcaption>
        mmHg. Dashed lines are the usual ({baseline.systolic}/{baseline.diastolic}).
        {sinceIdx > 0 && ' Shaded: since the rise began.'}
      </figcaption>
    </figure>
  );
}
