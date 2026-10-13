import type { FamilyView } from '../shared/contract';
import { navigate } from './nav';

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });

export default function FamilyHome({ view }: { view: FamilyView }) {
  const { senior, status, digest, handovers, contact } = view;
  const open = handovers.filter((h) => h.kind !== 'red_flag' || h.claimed_by);
  const quiet = status.rung_today !== 4 && status.rung_today !== 'R';

  return (
    <>
      <header className="care-header">
        <div>
          <p className="care-eyebrow">CareLoop SG · {contact.name}</p>
          <h1>{senior.name}</h1>
        </div>
        <button className="care-link" onClick={() => navigate('/care/pair')}>
          Settings
        </button>
      </header>

      <section className={`care-status ${quiet ? 'is-quiet' : 'is-action'}`}>
        <p className="care-status-line">{status.week_line}</p>
        <p className="care-muted">As of {fmtDate(status.as_of)}</p>
      </section>

      {open.map((h) => (
        <button key={h.id} className="care-card care-card-handover" onClick={() => navigate(`/care/handover/${h.id}`)}>
          <span className="care-card-title">
            {h.kind === 'red_flag' ? 'Red flag' : 'Needs a next step'}
            {h.claimed_by_name && <span className="care-pill">{h.claimed_by_name} is handling it</span>}
          </span>
          <span>{h.evidence.summary}</span>
          <span className="care-card-cta">See the evidence →</span>
        </button>
      ))}

      {digest && senior.consent.family_sees !== 'nothing' && (
        <section className="care-card">
          <h2>Week of {fmtDate(digest.week_of)}</h2>
          <ul className="care-digest">
            {digest.lines.slice(0, 5).map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </section>
      )}

      {senior.consent.family_sees === 'nothing' && (
        <section className="care-card care-muted">
          {senior.name} has chosen not to share a weekly digest. You will still be told about red flags straight away.
        </section>
      )}
    </>
  );
}
