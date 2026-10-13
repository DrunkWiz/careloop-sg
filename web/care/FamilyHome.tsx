import type { FamilyView, LogDay } from '../shared/contract';
import { digestLines } from './digest';
import { KIND_TITLE } from './HandoverView';
import Timeline from './Timeline';
import { plainSummary } from './plain';
import { navigate } from './nav';

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });

export function initials(name: string) {
  return name
    .replace(/^(Mr|Mrs|Mdm|Ms|Dr|Mx)\.?\s+/i, '')
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

export default function FamilyHome({ view, log }: { view: FamilyView; log: LogDay[] | null }) {
  const { senior, status, digest, handovers, contact, family_sees } = view;
  const open = handovers.filter((h) => h.status === 'open');
  const recent = handovers.filter((h) => h.status !== 'open');
  const quietRun = log ? log.findIndex((d) => d.rung !== '0') : -1;
  const quietDays = log ? (quietRun === -1 ? log.length : quietRun) : 0;

  const tone = status === 'red_flag' ? 'red' : status === 'handover' ? 'handover' : 'quiet';
  const headline =
    status === 'red_flag'
      ? 'Red flag reported'
      : status === 'handover'
        ? 'Needs you'
        : digest?.headline === 'worth a look'
          ? 'Mostly steady'
          : 'All quiet';
  const line =
    status === 'red_flag'
      ? 'Everyone in the family was told at once. See below.'
      : status === 'handover'
        ? `CareLoop has stopped nudging ${senior.name} and is waiting for someone to pick a next step.`
        : quietDays >= 2
          ? `${quietDays} quiet days in a row. CareLoop checked every day and found nothing to tell you.`
          : 'CareLoop checks every day and only tells you when something is different for them.';

  const redMsg = [...view.red_flags]
    .sort((a, b) => b.time.localeCompare(a.time))
    .find((m) => m.contact_id === contact.id) ?? view.red_flags[0];

  return (
    <>
      <header className="care-header">
        <p className="care-eyebrow">CareLoop SG · {contact.name}</p>
        <button className="care-link" onClick={() => navigate('/care/pair')}>
          Settings
        </button>
      </header>

      <section className={`hero is-${tone}`}>
        <div className="hero-top">
          <span className="avatar" aria-hidden="true">
            {initials(senior.name)}
          </span>
          <div>
            <h1>{senior.name}</h1>
            <span className={`hero-pill is-${tone}`}>{headline}</span>
          </div>
        </div>
        <p className="hero-line">{line}</p>
        <p className="hero-asof">As of {fmtDate(view.today)}</p>
      </section>

      {redMsg && (
        <section className="care-card care-card-red">
          <span className="care-card-title is-red">
            Red flag · {new Date(redMsg.time).toLocaleString('en-SG', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
          </span>
          <p>{redMsg.text}</p>
        </section>
      )}

      {[...open, ...recent].map((h) => (
        <button key={h.id} className={`care-card care-card-handover ${h.status !== 'open' ? 'is-done' : ''}`} onClick={() => navigate(`/care/handover/${h.id}`)}>
          <span className="care-card-title">
            {KIND_TITLE[h.kind]}
            {h.status !== 'open' && (
              <span className="care-pill">{h.claimed_by === contact.id ? 'You are' : `${h.claimed_by_name ?? 'Someone'} is`} handling it</span>
            )}
          </span>
          <span>{plainSummary(h, senior.name)}</span>
          <span className="care-card-cta">{h.status === 'open' ? 'See the evidence and pick a step →' : 'See the evidence and next steps →'}</span>
        </button>
      ))}

      {log && log.length > 0 && <Timeline log={log} name={senior.name} />}

      {digest && (
        <section className="care-card">
          <h2>
            This week: {fmtDate(digest.week_start)} to {fmtDate(digest.week_end)}
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
