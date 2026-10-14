// The "what CareLoop noticed" cards: plain-statistics findings from /insights, things to watch first.
import type { Finding } from '../shared/contract';

const ICON: Record<Finding['tone'], string> = { watch: '▲', good: '✓', neutral: '•' };
const LABEL: Record<Finding['tone'], string> = { watch: 'Worth watching', good: 'Going well', neutral: 'Good to know' };

export default function Findings({ findings, note, limit }: { findings: Finding[]; note?: string; limit?: number }) {
  const shown = limit ? findings.slice(0, limit) : findings;
  return (
    <div className="findings">
      {shown.map((f) => (
        <article key={f.id} className={`finding is-${f.tone}`}>
          <span className="finding-icon" aria-hidden="true">{ICON[f.tone]}</span>
          <div>
            <p className="finding-tone">{LABEL[f.tone]}</p>
            <h3>{f.title}</h3>
            <p>{f.detail}</p>
            <p className="finding-n">Based on {f.n} {f.n === 1 ? 'day' : 'days'} of their data</p>
          </div>
        </article>
      ))}
      {note && <p className="care-muted findings-note">{note}</p>}
    </div>
  );
}
