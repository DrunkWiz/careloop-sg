// The handover pack (rung 4 or R), shared by the family view and the AAC view.
import { useState } from 'react';
import type { Handover, HandoverKind, LogDay, SeniorRef } from '../shared/contract';
import { claimHandover, briefPdfUrl } from '../shared/api';
import BpChart from './BpChart';
import DecisionInfo from './DecisionInfo';
import NextSteps from './NextSteps';
import { plainSummary, ruleText } from './plain';
import { navigate } from './nav';

export const KIND_TITLE: Record<HandoverKind, string> = {
  bp_drift: 'Blood pressure above their usual',
  missed_medicine: 'Missed medicine',
  unwell: 'Not feeling well',
  activity: 'Less active and less in touch',
  no_contact: 'No contact',
  double_dose: 'Possible double dose',
  red_flag: 'Red flag',
};

const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });
const fmtTime = (d: string) =>
  new Date(d).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

interface Props {
  handover: Handover | undefined;
  senior: SeniorRef;
  contactId: string; // who claims: the family contact, or the AAC worker's contact for this senior
  claimerName?: (contactId: string) => string | null;
  others: string[]; // names of the other people who can claim it
  fromName: string; // who signs a drafted note
  log?: LogDay[] | null;
  backPath: string;
  onClaimed: (h: Handover) => void;
}

export default function HandoverView({ handover: h, senior, contactId, claimerName, others, fromName, log, backPath, onClaimed }: Props) {
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
  const hasNumbers = evidence.bp_series.some((p) => p.systolic != null) && evidence.baseline;
  const mine = h.claimed_by === contactId;
  const who = h.claimed_by ? (mine ? 'You are' : `${h.claimed_by_name ?? claimerName?.(h.claimed_by) ?? 'Someone'} is`) : '';
  const pdf = briefPdfUrl(senior.id);

  const claim = async () => {
    if (!choice) return;
    setBusy(true);
    setError(null);
    try {
      onClaimed(await claimHandover(h.id, contactId, choice));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <BackLink to={backPath} />
      <p className="care-eyebrow">
        {senior.name} · {KIND_TITLE[h.kind]}
      </p>
      <h1>{h.status === 'open' ? 'CareLoop needs you to pick a next step' : KIND_TITLE[h.kind]}</h1>
      <p className="care-lead">{plainSummary(h, senior.name)}</p>
      <p className="care-engine">
        The rule's own words: {cap(evidence.summary)}.
      </p>

      {hasNumbers && evidence.baseline && (
        <section className="care-card">
          <h2>Last 14 days</h2>
          <BpChart series={evidence.bp_series} baseline={evidence.baseline} flagged={evidence.dates} />
        </section>
      )}
      {!hasNumbers && h.kind === 'bp_drift' && (
        <p className="care-muted">{senior.name} has not chosen to share readings, so numbers are left out.</p>
      )}

      {evidence.tried.length > 0 && (
        <section className="care-card">
          <h2>What CareLoop already tried</h2>
          <ol className="care-timeline">
            {evidence.tried.map((t, i) => (
              <li key={i}>
                <span className="care-timeline-date">{fmtDate(t.date)}</span>
                <span>
                  {log?.find((d) => d.date === t.date)?.rule_id ? (
                    <>
                      {ruleText(log.find((d) => d.date === t.date)!.rule_id, t.rung)}
                      <span className="care-engine-inline">{cap(t.what)}.</span>
                    </>
                  ) : (
                    <>{cap(t.what)}.</>
                  )}
                </span>
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
              <strong>{who} handling this</strong>
              {h.claimed_at && <> since {fmtTime(h.claimed_at)}</>}.
            </p>
            {h.choice && <p className="care-muted">Chosen: {h.options.find((o) => o.id === h.choice)?.label ?? h.choice}</p>}
            {mine && others.length > 0 && <p className="care-muted">{others.join(' and ')} can see this.</p>}
          </div>
        ) : (
          <>
            <div className="care-options" role="radiogroup" aria-label="Next step">
              {h.options.map((o) => (
                <label key={o.id} className={`care-option ${choice === o.id ? 'is-selected' : ''}`}>
                  <input type="radio" name="next-step" value={o.id} checked={choice === o.id} onChange={() => setChoice(o.id)} />
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

      {h.claimed_by && mine && <NextSteps h={h} senior={senior} from={fromName} />}

      <DecisionInfo ruleId={log?.find((d) => d.decision_id === h.decision_id)?.rule_id ?? null} day={log?.find((d) => d.decision_id === h.decision_id) ?? null} />

      <section className="care-card">
        <h2>For the doctor</h2>
        <p className="care-muted">
          A one-page brief with 90 days of readings, medicines and what {senior.name} reported, to print or bring to the visit.
        </p>
        {pdf ? (
          <a className="care-secondary" href={pdf} target="_blank" rel="noreferrer">
            Open GP brief (PDF)
          </a>
        ) : (
          <button className="care-secondary" disabled>
            GP brief needs the API
          </button>
        )}
      </section>
    </>
  );
}

export function BackLink({ to, label = 'Back' }: { to: string; label?: string }) {
  return (
    <button className="care-link care-back" onClick={() => navigate(to)}>
      ← {label}
    </button>
  );
}
