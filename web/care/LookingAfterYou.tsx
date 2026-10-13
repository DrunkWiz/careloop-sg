// Looking after you: a private check-in for the caregiver, and where to get help in Singapore.
// The check-in stays on this device (localStorage): it is about the caregiver, not the senior, and nobody
// else sees it. Support details from AIC and MOH (see docs/user-research.md); check amounts with AIC.
import { useState } from 'react';

const KEY = 'careloop-you';

type Feeling = 'ok' | 'stretched' | 'struggling';

function load(): { feeling: Feeling; date: string } | null {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? 'null');
  } catch {
    return null;
  }
}

const ADVICE: Record<Feeling, string> = {
  ok: "Good. Keep a bit of the week for yourself, even when it's busy.",
  stretched: 'Most caregivers feel this at some point. Could someone else take one to-do this week? You can ask in the shared to-dos.',
  struggling: "You don't have to do this alone. Call AIC (below) about respite care or caregiver support. If you feel unsafe, call SOS on 1767.",
};

export default function LookingAfterYou() {
  const [last, setLast] = useState(load);
  const pick = (feeling: Feeling) => {
    const v = { feeling, date: new Date().toISOString().slice(0, 10) };
    try {
      localStorage.setItem(KEY, JSON.stringify(v));
    } catch {
      /* kept for this page only */
    }
    setLast(v);
  };
  return (
    <>
      <section className="care-card you">
        <h2>How are you doing?</h2>
        <p className="care-muted">Just for you. This stays on this phone and isn't shared with anyone.</p>
        <div className="you-options" role="radiogroup" aria-label="How are you doing?">
          {(
            [
              ['ok', 'Doing OK'],
              ['stretched', 'Stretched'],
              ['struggling', 'Struggling'],
            ] as const
          ).map(([id, label]) => (
            <button key={id} role="radio" aria-checked={last?.feeling === id} className={`you-option is-${id} ${last?.feeling === id ? 'is-on' : ''}`} onClick={() => pick(id)}>
              {label}
            </button>
          ))}
        </div>
        {last && <p className="you-advice">{ADVICE[last.feeling]}</p>}
      </section>

      <section className="care-card">
        <h2>Help for caregivers in Singapore</h2>
        <ul className="act-list">
          <li className="act-item">
            <span className="act-kind is-aac">AIC</span>
            <span className="act-body">
              <strong>Agency for Integrated Care hotline</strong>
              <span className="care-muted">Care services, respite care and caregiver grants. Mon–Fri 8.30am–8.30pm, Sat 8.30am–4pm.</span>
            </span>
            <a className="care-link" href="tel:18006506060">1800 650 6060</a>
          </li>
          <li className="act-item">
            <span className="act-kind">Break</span>
            <span className="act-body">
              <strong>Respite care</strong>
              <span className="care-muted">A day at a senior care centre, or a stay in a nursing home while you rest. Half of caregivers don't know it exists.</span>
            </span>
            <a className="care-link" href="https://www.moh.gov.sg/newsroom/variety-of-respite-care-options-available-for-caregivers-of-frail-seniors/" target="_blank" rel="noreferrer">Options</a>
          </li>
          <li className="act-item">
            <span className="act-kind">Grants</span>
            <span className="act-body">
              <strong>Home Caregiving Grant, Caregivers Training Grant</strong>
              <span className="care-muted">Monthly help with care costs, and subsidised caregiving courses. Check eligibility with AIC.</span>
            </span>
            <a className="care-link" href="https://moh.gov.sg/caregiver-support" target="_blank" rel="noreferrer">MOH</a>
          </li>
          <li className="act-item">
            <span className="act-kind">Talk</span>
            <span className="act-body">
              <strong>Samaritans of Singapore (SOS)</strong>
              <span className="care-muted">24 hours, if it all feels too much.</span>
            </span>
            <a className="care-link" href="tel:1767">1767</a>
          </li>
        </ul>
      </section>
    </>
  );
}
