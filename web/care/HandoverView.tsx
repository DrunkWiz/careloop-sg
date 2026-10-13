// The handover pack (rung 4), shared by the family view and the AAC view.
import { useState } from 'react';
import type { Contact, Handover, Senior } from '../shared/contract';
import { claimHandover, briefPdfUrl } from '../shared/api';
import BpChart from './BpChart';
import { navigate } from './nav';

const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });
const fmtTime = (d: string) =>
  new Date(d).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

interface Props {
  handover: Handover | undefined;
  senior: Senior;
  contact: Contact;
  others: string[]; // names of the other people who can claim it
  showNumbers: boolean;
  backPath: string;
  onClaimed: (h: Handover) => void;
}

export default function HandoverView({ handover: h, senior, contact, others, showNumbers, backPath, onClaimed }: Props) {
  const [choice, setChoice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!h) {
    return (
      <>
        <BackLink to={backPath} />
        <p className="care-muted">This handover is no longer open.</p>
      </>
    );
  }

  const { evidence } = h;
  const mine = h.claimed_by === contact.id;
  const pdf = briefPdfUrl(senior.id);

  const claim = async () => {
    if (!choice) return;
    setBusy(true);
    setError(null);
    try {
      onClaimed(await claimHandover(h.id, contact.id, choice));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <BackLink to={backPath} />
      <p className="care-eyebrow">{senior.name}</p>
      <h1>{h.kind === 'red_flag' ? 'Red flag' : 'CareLoop needs you to pick a next step'}</h1>
      <p className="care-lead">{evidence.summary}</p>

      {showNumbers && evidence.bp_series && evidence.baseline && (
        <section className="care-card">
          <h2>Last 14 days</h2>
          <BpChart series={evidence.bp_series} baseline={evidence.baseline} since={evidence.since} />
        </section>
      )}
      {!showNumbers && evidence.bp_series && (
        <p className="care-muted">{senior.name} has not chosen to share readings, so numbers are left out.</p>
      )}

      {evidence.tried.length > 0 && (
        <section className="care-card">
          <h2>What CareLoop already tried</h2>
          <ol className="care-timeline">
            {evidence.tried.map((t, i) => (
              <li key={i}>
                <span className="care-timeline-date">{fmtDate(t.date)}</span>
                <span>{t.what}</span>
              </li>
            ))}
          </ol>
          <p className="care-muted">CareLoop has stopped nudging. It does nothing more until someone picks a step.</p>
        </section>
      )}

      <section className="care-card">
        <h2>Next step</h2>
        {h.claimed_by ? (
          <div className="care-claimed">
            <p>
              <strong>{mine ? 'You are' : `${h.claimed_by_name} is`} handling this</strong>
              {h.claimed_at && <> since {fmtTime(h.claimed_at)}</>}.
            </p>
            {h.chosen_option && (
              <p className="care-muted">Chosen: {h.options.find((o) => o.id === h.chosen_option)?.label}</p>
            )}
            {mine && others.length > 0 && <p className="care-muted">{others.join(' and ')} can see this.</p>}
          </div>
        ) : (
          <>
            <div className="care-options" role="radiogroup" aria-label="Next step">
              {h.options.map((o) => (
                <label key={o.id} className={`care-option ${choice === o.id ? 'is-selected' : ''}`}>
                  <input
                    type="radio"
                    name="next-step"
                    value={o.id}
                    checked={choice === o.id}
                    onChange={() => setChoice(o.id)}
                  />
                  {o.label}
                </label>
              ))}
            </div>
            <button className="care-primary" disabled={!choice || busy} onClick={claim}>
              {busy ? 'Saving…' : "I'll handle it"}
            </button>
            {others.length > 0 && <p className="care-muted">{others.join(' and ')} will see that you took this.</p>}
            {error && <p className="care-error">{error}</p>}
          </>
        )}
      </section>

      {evidence.bp_series && (
        <section className="care-card">
          <h2>For the doctor</h2>
          <p className="care-muted">
            A one-page brief with 90 days of readings, medicines and what {senior.name} reported, to print or bring to
            the visit.
          </p>
          {pdf ? (
            <a className="care-secondary" href={pdf} target="_blank" rel="noreferrer">
              Open GP brief (PDF)
            </a>
          ) : (
            <button className="care-secondary" disabled>
              GP brief: not built yet
            </button>
          )}
        </section>
      )}
    </>
  );
}

export function BackLink({ to }: { to: string }) {
  return (
    <button className="care-link care-back" onClick={() => navigate(to)}>
      ← Back
    </button>
  );
}
