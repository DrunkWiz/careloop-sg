// Settings and pairing. The caregiver makes a code (POST /care/pair-code); the senior enters it in the senior
// app, and the senior chooses there what the family sees. So consent is shown here, not set here.
import { useState } from 'react';
import type { FamilyView, PairCodeOut } from '../shared/contract';
import { createPairCode } from '../shared/api';
import { BackLink } from './HandoverView';

const SEES: Record<FamilyView['family_sees'], string> = {
  nothing: 'Only red flags.',
  digest: 'The weekly digest, without numbers. Red flags always.',
  readings: 'The weekly digest and blood pressure numbers. Red flags always.',
};

export default function Pairing({ view }: { view: FamilyView }) {
  const [form, setForm] = useState({ senior_name: '', home_postal: '' });
  const [result, setResult] = useState<PairCodeOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = form.senior_name.trim() && /^\d{6}$/.test(form.home_postal);

  const make = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await createPairCode({
          contact_name: view.contact.name,
          role: 'family',
          language: view.contact.language,
          senior_name: form.senior_name.trim(),
          home_postal: form.home_postal,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <BackLink to="/care" />
      <h1>Settings</h1>

      <section className="care-card">
        <h2>What {view.senior.name} shares with you</h2>
        <p>{SEES[view.family_sees]}</p>
        <p className="care-muted">
          {view.senior.name} chose this on their phone and can change it there. It is their choice.
        </p>
      </section>

      <AlertsCard />

      <section className="care-card">
        <h2>Family on CareLoop</h2>
        <ul className="care-digest">
          <li>{view.contact.name} (you)</li>
          {view.other_contacts.map((c) => (
            <li key={c.id}>{c.name}</li>
          ))}
        </ul>
        <p className="care-muted">Anyone here can take a handover. The first to tap “I'll handle it” owns it.</p>
      </section>

      <section className="care-card aac-form">
        <h2>Set up CareLoop for someone new</h2>
        {result ? (
          <>
            <p className="care-muted">Open CareLoop on their phone and enter this code. It works once.</p>
            <p className="care-code" aria-live="polite">
              {result.code.slice(0, 3)} {result.code.slice(3)}
            </p>
            <p className="care-muted">On their phone they choose what to share with you. Red flags are always shared.</p>
          </>
        ) : (
          <>
            <label>
              Their name
              <input value={form.senior_name} onChange={(e) => setForm({ ...form, senior_name: e.target.value })} placeholder="e.g. Mr Tan" />
            </label>
            <label>
              Home postal code
              <input
                inputMode="numeric"
                maxLength={6}
                value={form.home_postal}
                onChange={(e) => setForm({ ...form, home_postal: e.target.value.replace(/\D/g, '') })}
                placeholder="6 digits, for the haze reading"
              />
            </label>
            <button className="care-primary" disabled={!valid || busy} onClick={make}>
              {busy ? 'Making a code…' : 'Get a pairing code'}
            </button>
            {error && <p className="care-error">{error}</p>}
          </>
        )}
      </section>
    </>
  );
}

function AlertsCard() {
  const supported = 'Notification' in window;
  const [perm, setPerm] = useState(supported ? Notification.permission : 'denied');
  return (
    <section className="care-card">
      <h2>Alerts on this device</h2>
      {!supported ? (
        <p className="care-muted">This browser can't show alerts.</p>
      ) : perm === 'granted' ? (
        <p className="care-muted">On. While CareLoop is open in a tab, you'll get an alert for a red flag or a handover.</p>
      ) : perm === 'denied' ? (
        <p className="care-muted">Blocked in this browser's settings.</p>
      ) : (
        <button className="care-secondary" onClick={async () => setPerm(await Notification.requestPermission())}>
          Turn on alerts
        </button>
      )}
    </section>
  );
}
