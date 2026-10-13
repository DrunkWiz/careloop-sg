// Pairing: generate the code that links the senior app, and set what the family sees.
// No pairing endpoint in the contract yet; this is local-only until Vibu adds one.
import { useState } from 'react';
import type { ConsentShare, FamilyView } from '../shared/contract';
import { navigate } from './nav';

const SHARE_OPTIONS: { id: ConsentShare; label: string; detail: string }[] = [
  { id: 'nothing', label: 'Nothing', detail: 'Only red flags.' },
  { id: 'digest', label: 'Weekly digest', detail: 'Five lines a week on how it went. No numbers.' },
  { id: 'readings', label: 'Digest and readings', detail: 'The digest, plus blood pressure numbers when CareLoop hands over.' },
];

function newCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

export default function Pairing({ view }: { view: FamilyView }) {
  const [code, setCode] = useState<string | null>(null);
  const [share, setShare] = useState<ConsentShare>(view.senior.consent.family_sees);

  return (
    <>
      <button className="care-link care-back" onClick={() => navigate('/care')}>
        ← Back
      </button>
      <h1>Set up {view.senior.name}'s app</h1>

      <section className="care-card">
        <h2>1. Link the senior app</h2>
        <p className="care-muted">Open CareLoop on their phone and enter this code. It works for 15 minutes.</p>
        {code ? (
          <p className="care-code" aria-live="polite">
            {code.slice(0, 3)} {code.slice(3)}
          </p>
        ) : (
          <button className="care-primary" onClick={() => setCode(newCode())}>
            Get a pairing code
          </button>
        )}
      </section>

      <section className="care-card">
        <h2>2. What the family sees</h2>
        <p className="care-muted">Choose this together with {view.senior.name}. It is their choice, and they can change it.</p>
        <div className="care-options" role="radiogroup" aria-label="What the family sees">
          {SHARE_OPTIONS.map((o) => (
            <label key={o.id} className={`care-option ${share === o.id ? 'is-selected' : ''}`}>
              <input type="radio" name="share" value={o.id} checked={share === o.id} onChange={() => setShare(o.id)} />
              <span>
                <strong>{o.label}</strong>
                <span className="care-option-detail">{o.detail}</span>
              </span>
            </label>
          ))}
        </div>
        <p className="care-notice">Red flags are always shared with the family, whatever is chosen here.</p>
      </section>

      <section className="care-card">
        <h2>Family on CareLoop</h2>
        <ul className="care-digest">
          {view.family.map((c) => (
            <li key={c.id}>
              {c.name}
              {c.id === view.contact.id && ' (you)'}
            </li>
          ))}
        </ul>
        <p className="care-muted">Anyone here can take a handover. The first to tap “I'll handle it” owns it.</p>
      </section>
    </>
  );
}
