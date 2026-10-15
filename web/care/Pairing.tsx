// Settings and pairing. The caregiver makes a code (POST /care/pair-code); the senior enters it in the senior
// app, and the senior chooses there what the family sees. So consent is shown here, not set here.
//
// The pairing section has TWO clear cards:
//
//   1. "Add a family member" — for bringing a sibling, spouse, or friend into the care of someone
//      who is ALREADY on CareLoop. The pair code creates a NEW caregiver linked to an existing
//      senior.
//
//   2. "Add someone new" — for an elderly you look after who is NOT on CareLoop yet. A new senior
//      is created and linked to the current caregiver.
//
// When view is provided (the normal settings tab), the consent and family sections are shown.
// When only caregiver is provided (a caregiver with no seniors yet), only the pairing form is shown.
import { useState } from 'react';
import type { CaregiverSenior, FamilyView, Lang, PairCodeOut } from '../shared/contract';
import { createPairCode } from '../shared/api';

interface PairingCaregiver {
  id: string;
  name: string;
  language: Lang;
  seniors?: CaregiverSenior[];
}

const SEES: Record<FamilyView['family_sees'], string> = {
  nothing: 'Only red flags.',
  digest: 'The weekly digest, without numbers. Red flags always.',
  readings: 'The weekly digest and blood pressure numbers. Red flags always.',
};

export default function Pairing({ view, caregiver }: { view?: FamilyView; caregiver?: PairingCaregiver }) {
  const cg = caregiver ?? (view ? { id: view.contact.caregiver_id, name: view.contact.name, language: view.contact.language } : null);
  if (!cg) return null;

  // Existing seniors the "add a family member" path can target. When a single FamilyView is open we
  // default to that senior; if the caregiver looks after several we offer them all.
  const existingSeniors: CaregiverSenior[] = caregiver?.seniors ?? (
    view
      ? [{ contact_id: view.contact.id, senior_id: view.senior.id, senior_name: view.senior.name, primary: view.contact.primary, status: 'quiet', on_duty: view.on_duty }]
      : []
  );

  return (
    <>
      {view && (
        <>
          <h2 className="care-section-title">Settings</h2>

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
            <p className="care-muted">Anyone here can take a handover. The first to tap "I'll handle it" owns it.</p>
          </section>
        </>
      )}

      <h2 className="care-section-title">Add a person</h2>
      <p className="care-muted">Pick the situation. Codes are always entered in CareLoop on the senior's phone.</p>

      {existingSeniors.length > 0 && (
        <AddCaregiverCard caregiver={cg} seniors={existingSeniors} />
      )}

      <NewSeniorCard caregiver={cg} />
    </>
  );
}

function AddCaregiverCard({ caregiver, seniors }: { caregiver: PairingCaregiver; seniors: CaregiverSenior[] }) {
  const [target, setTarget] = useState<string>(seniors[0]?.senior_id ?? '');
  const [contactName, setContactName] = useState('');
  const [result, setResult] = useState<PairCodeOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const senior = seniors.find((s) => s.senior_id === target);
  const valid = contactName.trim().length > 0 && !!target;

  const make = async () => {
    setBusy(true);
    setError(null);
    try {
      // caregiver_id is None on purpose: we are creating a NEW caregiver who will be linked to the
      // existing senior once they redeem the code. The current caregiver (this app's user) is just
      // the inviter.
      setResult(
        await createPairCode({
          caregiver_id: null,
          contact_name: contactName.trim(),
          role: 'family',
          language: caregiver.language,
          senior_id: target,
          senior_name: senior?.senior_name ?? '',
          home_postal: '560000',
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    return (
      <section className="care-card aac-form">
        <h2>Code for {contactName.trim()}</h2>
        <p className="care-muted">Enter this code in CareLoop on {senior?.senior_name}'s phone. {contactName.trim()} then joins {senior?.senior_name}'s care team. It works once.</p>
        <p className="care-code" aria-live="polite">
          {result.code.slice(0, 3)} {result.code.slice(3)}
        </p>
        <p className="care-muted">{senior?.senior_name} chooses what {contactName.trim()} can see. Red flags always reach everyone on the care team.</p>
      </section>
    );
  }

  return (
    <section className="care-card aac-form">
      <h2>Add a family member</h2>
      <p className="care-muted">
        Need a hand looking after {senior?.senior_name ?? 'them'}? Add a sibling, spouse or friend to the care team.
        You'll get a code to enter on {senior?.senior_name ?? 'their'}'s phone.
      </p>
      {seniors.length > 1 && (
        <label>
          Looking after
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            {seniors.map((s) => (
              <option key={s.senior_id} value={s.senior_id}>{s.senior_name}{s.primary ? ' (you are primary)' : ''}</option>
            ))}
          </select>
        </label>
      )}
      <label>
        Their name
        <input
          value={contactName}
          onChange={(e) => setContactName(e.target.value)}
          placeholder="e.g. Your brother, your wife"
        />
      </label>
      <button className="care-primary" disabled={!valid || busy} onClick={make}>
        {busy ? 'Making a code…' : 'Get a code for them'}
      </button>
      {error && <p className="care-error">{error}</p>}
    </section>
  );
}

function NewSeniorCard({ caregiver }: { caregiver: PairingCaregiver }) {
  const [form, setForm] = useState({ senior_name: '', home_postal: '' });
  const [result, setResult] = useState<PairCodeOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = form.senior_name.trim().length > 0 && /^\d{6}$/.test(form.home_postal);

  const make = async () => {
    setBusy(true);
    setError(null);
    try {
      // caregiver_id is the CURRENT caregiver (this app's user). The pair code creates a NEW senior
      // linked to them when the new senior redeems it on their phone.
      setResult(
        await createPairCode({
          caregiver_id: caregiver.id,
          contact_name: caregiver.name,
          role: 'family',
          language: caregiver.language,
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

  if (result) {
    return (
      <section className="care-card aac-form">
        <h2>Code for {form.senior_name.trim()}</h2>
        <p className="care-muted">Open CareLoop on {form.senior_name.trim()}'s phone and enter this code. It works once.</p>
        <p className="care-code" aria-live="polite">
          {result.code.slice(0, 3)} {result.code.slice(3)}
        </p>
        <p className="care-muted">{form.senior_name.trim()} chooses what you can see. Red flags always reach you.</p>
      </section>
    );
  }

  return (
    <section className="care-card aac-form">
      <h2>Add someone new</h2>
      <p className="care-muted">
        Look after another elderly who isn't on CareLoop yet? Set them up here. We'll link them to you
        so you get alerts for them too.
      </p>
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
        {busy ? 'Making a code…' : 'Get a code for them'}
      </button>
      {error && <p className="care-error">{error}</p>}
    </section>
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
