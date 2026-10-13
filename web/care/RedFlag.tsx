// Full-screen red flag. Shown immediately, whatever the senior's sharing choices: red flags are always shared.
import { useState } from 'react';
import type { Contact, Handover, Senior } from '../shared/contract';
import { claimHandover } from '../shared/api';

const fmtTime = (d: string) =>
  new Date(d).toLocaleString('en-SG', { weekday: 'short', hour: 'numeric', minute: '2-digit' });

interface Props {
  senior: Senior;
  contact: Contact;
  handover: Handover;
  onClaimed: (h: Handover) => void;
}

export default function RedFlag({ senior, contact, handover, onClaimed }: Props) {
  const [busy, setBusy] = useState(false);
  const r = handover.evidence.reported;
  const aac = contact.role === 'aac';

  const take = async (optionId: string) => {
    setBusy(true);
    try {
      onClaimed(await claimHandover(handover.id, contact.id, optionId));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="red-flag" role="alertdialog" aria-labelledby="rf-title">
      <p className="red-flag-eyebrow">Red flag · {senior.name}</p>
      <h1 id="rf-title">{handover.evidence.summary}</h1>
      {r && (
        <dl className="red-flag-facts">
          {r.reading && (
            <>
              <dt>Reading</dt>
              <dd className="red-flag-number">
                {r.reading.systolic}/{r.reading.diastolic}
              </dd>
            </>
          )}
          <dt>Said</dt>
          <dd>“{r.words}”</dd>
          <dt>When</dt>
          <dd>{fmtTime(r.time)}</dd>
        </dl>
      )}
      <div className="red-flag-actions">
        {handover.options.map((o, i) => (
          <button
            key={o.id}
            className={i === 0 ? 'red-flag-primary' : 'red-flag-secondary'}
            disabled={busy}
            onClick={() => take(o.id)}
          >
            {o.label}
          </button>
        ))}
      </div>
      <p className="red-flag-note">
        Tapping a step tells {aac ? 'your colleagues' : 'the rest of the family'} you are handling it.
        {aac && ' Follow your centre’s own escalation protocol as well.'} If there is chest pain, face drooping,
        slurred speech or weakness on one side, call 995.
      </p>
    </div>
  );
}
