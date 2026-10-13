// Full-screen red flag. Shown at once, whatever the senior's sharing choices: red flags are always shared.
// Works from the red-flag handover when there is one, and from the red-flag message when there isn't.
import { useState } from 'react';
import type { Handover, Message, SeniorRef } from '../shared/contract';
import { claimHandover } from '../shared/api';
import DecisionInfo from './DecisionInfo';

const fmtTime = (d: string) => new Date(d).toLocaleString('en-SG', { weekday: 'short', hour: 'numeric', minute: '2-digit' });

interface Props {
  senior: SeniorRef;
  contactId: string;
  aac: boolean;
  handover: Handover | null;
  message: Message | null;
  reason?: string | null; // the day's decision reason, when there is neither handover nor message
  onClaimed: (h: Handover) => void;
  onSeen: () => void; // no handover to claim: the person says they've seen it
}

export default function RedFlag({ senior, contactId, aac, handover, message, reason, onClaimed, onSeen }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const summary = handover?.evidence.summary ?? reason ?? null;
  const when = message?.time ?? handover?.opened_at ?? null;

  const take = async (optionId: string) => {
    if (!handover) return;
    setBusy(true);
    setError(null);
    try {
      onClaimed(await claimHandover(handover.id, contactId, optionId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="red-flag" role="alertdialog" aria-labelledby="rf-title">
      <p className="red-flag-eyebrow">Red flag · {senior.name}</p>
      <h1 id="rf-title">{message?.text ?? `${senior.name} reported a red flag.`}</h1>
      <dl className="red-flag-facts">
        {summary && (
          <>
            <dt>What CareLoop saw</dt>
            <dd>{summary.charAt(0).toUpperCase() + summary.slice(1)}</dd>
          </>
        )}
        {when && (
          <>
            <dt>When</dt>
            <dd>{fmtTime(when)}</dd>
          </>
        )}
      </dl>
      <div className="red-flag-actions">
        {handover ? (
          handover.options.map((o, i) => (
            <button
              key={o.id}
              className={i === 0 ? 'red-flag-primary' : 'red-flag-secondary'}
              disabled={busy}
              onClick={() => take(o.id)}
            >
              {o.label}
            </button>
          ))
        ) : (
          <button className="red-flag-primary" onClick={onSeen}>
            I've seen this
          </button>
        )}
      </div>
      <a className="red-flag-995" href="tel:995">
        Dial 995 now
      </a>
      {error && <p className="red-flag-note">{error}</p>}
      <p className="red-flag-note">
        {handover
          ? `Tapping a step tells ${aac ? 'your centre' : 'the rest of the family'} you are handling it.`
          : `Everyone ${aac ? 'at your centre' : 'in the family'} who is linked got this message too.`}
        {aac && ' Follow your centre’s own escalation protocol as well.'} If there is chest pain, face drooping, slurred
        speech or weakness on one side, call 995.
      </p>
      <div className="red-flag-info">
        <DecisionInfo ruleId={null} message={message} />
      </div>
    </div>
  );
}
