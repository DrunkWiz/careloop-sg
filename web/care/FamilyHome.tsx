import type { FamilyView } from '../shared/contract';
import { digestLines } from './digest';
import { KIND_TITLE } from './HandoverView';
import { navigate } from './nav';

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });

export default function FamilyHome({ view }: { view: FamilyView }) {
  const { senior, status, digest, handovers, contact, family_sees } = view;
  const open = handovers.filter((h) => h.status === 'open');
  const recent = handovers.filter((h) => h.status !== 'open');

  const statusLine =
    status === 'red_flag'
      ? `${senior.name} reported a red flag. See below.`
      : status === 'handover'
        ? `CareLoop needs you to pick a next step for ${senior.name}.`
        : digest?.headline === 'worth a look'
          ? `A mostly steady week for ${senior.name}. One thing is noted below.`
          : `All quiet for ${senior.name}.`;

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

      <section className={`care-status ${status === 'quiet' ? 'is-quiet' : 'is-action'}`}>
        <p className="care-status-line">{statusLine}</p>
        <p className="care-muted">As of {fmtDate(view.today)}</p>
      </section>

      {[...view.red_flags]
        .sort((a, b) => b.time.localeCompare(a.time))
        .filter((m, i, all) => m.contact_id === contact.id || (i === 0 && !all.some((x) => x.contact_id === contact.id)))
        .slice(0, 1)
        .map((m) => (
        <section key={m.id} className="care-card care-card-red">
          <span className="care-card-title is-red">Red flag · {new Date(m.time).toLocaleString('en-SG', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}</span>
          <p>{m.text}</p>
        </section>
      ))}

      {[...open, ...recent].map((h) => (
        <button key={h.id} className="care-card care-card-handover" onClick={() => navigate(`/care/handover/${h.id}`)}>
          <span className="care-card-title">
            {KIND_TITLE[h.kind]}
            {h.status !== 'open' && (
              <span className="care-pill">{h.claimed_by === contact.id ? 'You are' : `${h.claimed_by_name ?? 'Someone'} is`} handling it</span>
            )}
          </span>
          <span>{capitalise(h.evidence.summary)}.</span>
          <span className="care-card-cta">{h.status === 'open' ? 'See the evidence and pick a step →' : 'See the evidence →'}</span>
        </button>
      ))}

      {digest && (
        <section className="care-card">
          <h2>
            Week of {fmtDate(digest.week_start)} to {fmtDate(digest.week_end)}
          </h2>
          <ul className="care-digest">
            {digestLines(digest, senior.name).map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </section>
      )}

      {family_sees === 'nothing' && (
        <section className="care-card care-muted">
          {senior.name} has chosen not to share a weekly digest. You will still be told about red flags straight away.
        </section>
      )}
    </>
  );
}

export function capitalise(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
