// Help with the step someone just took on a handover, so claiming it isn't a dead end.
// Fixed templates filled from the evidence. Nothing here is medical advice, and nothing is sent by CareLoop:
// the person copies or shares it themselves.
import { useState } from 'react';
import type { Handover, SeniorRef } from '../shared/contract';
import { briefPdfUrl } from '../shared/api';
import { cap, plainSummary } from './plain';

const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short' });

function gpNote(h: Handover, senior: SeniorRef, from: string): string {
  const readings = h.evidence.bp_series
    .filter((p) => p.systolic != null && p.diastolic != null)
    .slice(-7)
    .map((p) => `${fmtDate(p.date)}: ${p.systolic}/${p.diastolic}`)
    .join(', ');
  return [
    'Dear Doctor,',
    '',
    `I'm writing about ${senior.name}, who sees you for high blood pressure.`,
    `CareLoop, the app we use to keep track of readings between visits, flagged this: ${plainSummary(h, senior.name)}`,
    readings ? `Home readings in the last week (mmHg): ${readings}.` : '',
    h.evidence.tried.length ? `What was already tried: ${h.evidence.tried.map((t) => `${fmtDate(t.date)}, ${t.what}`).join('; ')}.` : '',
    '',
    'Could we arrange a review? A one-page summary of the last 90 days is attached.',
    '',
    `Thank you,`,
    from,
  ]
    .filter((l, i, all) => l !== '' || all[i - 1] !== '')
    .join('\n');
}

function CopyShare({ text, title }: { text: string; title: string }) {
  const [done, setDone] = useState<string | null>(null);
  const flash = (s: string) => {
    setDone(s);
    setTimeout(() => setDone(null), 2000);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      flash('Copied');
    } catch {
      flash('Could not copy');
    }
  };
  const share = async () => {
    try {
      await navigator.share({ title, text });
    } catch {
      /* cancelled */
    }
  };
  return (
    <div className="ns-actions">
      <button className="care-secondary" onClick={copy}>
        {done ?? 'Copy'}
      </button>
      {'share' in navigator ? (
        <button className="care-secondary" onClick={share}>
          Share…
        </button>
      ) : null}
      <a className="care-secondary" href={`https://wa.me/?text=${encodeURIComponent(text)}`} target="_blank" rel="noreferrer">
        WhatsApp
      </a>
    </div>
  );
}

export default function NextSteps({ h, senior, from }: { h: Handover; senior: SeniorRef; from: string }) {
  const pdf = briefPdfUrl(senior.id);
  const choice = h.choice ?? '';

  if (choice === 'gp_note') {
    const text = gpNote(h, senior, from);
    return (
      <section className="care-card ns">
        <h2>Your note to the GP</h2>
        <p className="care-muted">A draft from the evidence. Edit it as you like before sending; CareLoop doesn't send it.</p>
        <pre className="ns-note">{text}</pre>
        <CopyShare text={text} title={`Note about ${senior.name}`} />
        {pdf && (
          <a className="care-link" href={pdf} target="_blank" rel="noreferrer">
            Attach the GP brief (PDF) →
          </a>
        )}
      </section>
    );
  }

  if (choice === 'polyclinic') {
    return (
      <section className="care-card ns">
        <h2>Booking a polyclinic visit</h2>
        <ol className="ns-list">
          <li>
            Book on the{' '}
            <a href="https://www.healthhub.sg/" target="_blank" rel="noreferrer">
              HealthHub app or site
            </a>{' '}
            ({senior.name}'s Singpass is needed), or call their polyclinic.
          </li>
          <li>Ask for a review of blood pressure. Mention home readings have been higher than usual.</li>
          <li>Bring: NRIC, all current medicines in their boxes, the home BP monitor, and the GP brief below.</li>
        </ol>
        {pdf && (
          <a className="care-secondary" href={pdf} target="_blank" rel="noreferrer">
            Open the GP brief to print
          </a>
        )}
      </section>
    );
  }

  if (choice === 'call' || choice === 'call_now' || choice === 'home_visit') {
    const visit = choice === 'home_visit';
    return (
      <section className="care-card ns">
        <h2>{visit ? 'For the visit' : 'For the call'}</h2>
        <ul className="ns-list">
          <li>Start with how they are, not their numbers. {senior.name} hasn't been shown the readings.</li>
          <li>Ask whether they've been taking their medicine as usual, and if any is running out.</li>
          <li>Ask if anything changed lately: sleep, food, stress, a new medicine.</li>
          {visit && <li>Check they have enough medicine at home and the BP monitor works.</li>}
          <li>Offer to help book a check-up. Don't suggest stopping or changing a medicine: that's for the doctor.</li>
          {h.kind === 'no_contact' && <li>If nobody answers at home, follow your centre's protocol for a senior who can't be reached.</li>}
        </ul>
        <p className="care-muted">{cap(plainSummary(h, senior.name))}</p>
      </section>
    );
  }

  if (choice === '995') {
    return (
      <section className="care-card ns">
        <h2>Calling 995</h2>
        <a className="care-primary is-alert" href="tel:995">
          Call 995
        </a>
        <p className="care-muted">Tell them: {cap(h.evidence.summary)}. Give the home address and say they have high blood pressure.</p>
      </section>
    );
  }

  return null;
}
