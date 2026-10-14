import type { FamilyView, LogDay } from '../shared/contract';
import { digestLines } from './digest';
import { KIND_TITLE } from './HandoverView';
import Timeline from './Timeline';
import { plainSummary } from './plain';
import { navigate } from './nav';
import Findings from './Findings';
import { useInsights } from './Health';
import { useActivities } from './ActivitiesView';
import { useCareNotes } from './CarePlan';
import type { FamilySees } from '../shared/contract';

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

      <TodaySoFar log={log} today={view.today} name={senior.name} shared={family_sees} />

      <PlanPreview seniorId={senior.id} contactId={contact.id} me={contact.name} today={view.today} />

      {redMsg && (
        <section className="care-card care-card-red">
          <span className="care-card-title is-red">
            Red flag · {new Date(redMsg.time).toLocaleString('en-SG', { weekday: 'short', hour: 'numeric', minute: '2-digit' })}
          </span>
          <p>{redMsg.text}</p>
        </section>
      )}

      {[...open, ...recent].map((h) => (
        <button key={h.id} className={`care-card care-card-handover ${h.status !== 'open' ? 'is-done' : ''}`} onClick={() => navigate(`/care/family/handover/${h.id}`)}>
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

      {view.family_sees !== 'nothing' && <NoticedPreview seniorId={senior.id} contactId={contact.id} />}

      {log && log.length > 0 && <Timeline log={log} name={senior.name} />}

      <ActivityPreview seniorId={senior.id} contactId={contact.id} name={senior.name} />

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

function NoticedPreview({ seniorId, contactId }: { seniorId: string; contactId: string }) {
  const { data } = useInsights(seniorId, contactId);
  if (!data?.findings.length) return null;
  return (
    <section className="care-section">
      <div className="card-head">
        <h2 className="care-section-title">What CareLoop noticed</h2>
        <button className="care-link" onClick={() => navigate('/care/family/health')}>
          All of it →
        </button>
      </div>
      <Findings findings={data.findings} limit={2} />
    </section>
  );
}

function ActivityPreview({ seniorId, contactId, name }: { seniorId: string; contactId: string; name: string }) {
  const a = useActivities(seniorId, contactId);
  const first = a?.suggested_today[0];
  if (!first) return null;
  return (
    <button className="care-card act-preview" onClick={() => navigate('/care/family/activities')}>
      <span className="care-eyebrow">
        Suggested to {name} today{a.indoor_only ? ` · indoor, it's ${a.why_indoor === 'rain' ? 'raining' : 'hazy'}` : ''}
      </span>
      <strong>{first.place}</strong>
      <span className="care-muted">{first.why_it_fits}</span>
      <span className="care-card-cta">See what else is on nearby →</span>
    </button>
  );
}

// Today at a glance: the three things a working or far-away child asks first. From today's log entry.
function TodaySoFar({ log, today, name, shared }: { log: LogDay[] | null; today: string; name: string; shared: FamilySees }) {
  const d = log?.find((x) => x.date === today);
  if (!log || shared === 'nothing') return null;
  const first = d?.checkins[0];
  const sg = (t: Date) => t.toLocaleTimeString('en-SG', { timeZone: 'Asia/Singapore', hour: 'numeric', minute: '2-digit' });
  const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const away = !!localTz && localTz !== 'Asia/Singapore';
  return (
    <section className="today" aria-label="Today so far">
      <div className={`today-item ${d?.replied ? 'is-yes' : 'is-no'}`}>
        <span className="today-icon" aria-hidden="true">{d?.replied ? '✓' : '…'}</span>
        <span>
          <strong>{d?.replied ? 'Checked in' : 'No check-in yet'}</strong>
          <span>{first ? sg(new Date(first.time)) : d?.replied ? 'today' : `${name} usually replies in the morning`}</span>
        </span>
      </div>
      <div className={`today-item ${d?.pills === 'taken' ? 'is-yes' : d?.pills === 'missed' ? 'is-warn' : 'is-no'}`}>
        <span className="today-icon" aria-hidden="true">{d?.pills === 'taken' ? '✓' : d?.pills === 'missed' ? '!' : '…'}</span>
        <span>
          <strong>{d?.pills === 'taken' ? 'Pills taken' : d?.pills === 'missed' ? 'Missed a dose' : 'Pills not reported'}</strong>
          <span>{d?.pills === 'missed' ? 'CareLoop asked gently' : 'today'}</span>
        </span>
      </div>
      <div className={`today-item ${d?.bp ? 'is-yes' : 'is-no'}`}>
        <span className="today-icon" aria-hidden="true">{d?.bp ? '♥' : '…'}</span>
        <span>
          <strong>{d?.bp ? `BP ${d.bp.systolic}/${d.bp.diastolic}` : shared === 'readings' ? 'No BP yet' : 'BP not shared'}</strong>
          <span>{shared === 'readings' ? 'today' : 'their choice'}</span>
        </span>
      </div>
      <p className="today-time">
        {sg(new Date())} in Singapore{away ? ` · ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} where you are` : ''}
      </p>
    </section>
  );
}

// The next visit and my open to-dos, from the shared care plan.
function PlanPreview({ seniorId, contactId, me, today }: { seniorId: string; contactId: string; me: string; today: string }) {
  const { notes } = useCareNotes(seniorId, contactId);
  if (!notes) return null;
  const next = [...notes.appointments].filter((a) => a.date >= today).sort((a, b) => a.date.localeCompare(b.date))[0];
  const mine = notes.tasks.filter((t) => !t.done && t.owner === me).length;
  const unowned = notes.tasks.filter((t) => !t.done && !t.owner).length;
  const questions = notes.questions.filter((q) => !q.asked).length;
  if (!next && !mine && !unowned) {
    return (
      <button className="care-card plan-preview is-empty" onClick={() => navigate('/care/family/plan')}>
        <span className="care-muted">No visit or to-dos in the care plan yet.</span>
        <span className="care-card-cta">Add the next appointment →</span>
      </button>
    );
  }
  return (
    <button className="care-card plan-preview" onClick={() => navigate('/care/family/plan')}>
      {next && (
        <span>
          <strong>Next visit {new Date(next.date).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' })}</strong>
          {next.place && ` · ${next.place}`}
          {questions > 0 && <span className="care-muted"> · {questions} question{questions > 1 ? 's' : ''} for the doctor</span>}
        </span>
      )}
      {(mine > 0 || unowned > 0) && (
        <span className="care-muted">
          {mine > 0 && `${mine} to-do${mine > 1 ? 's' : ''} for you`}
          {mine > 0 && unowned > 0 && ' · '}
          {unowned > 0 && `${unowned} nobody has taken yet`}
        </span>
      )}
      <span className="care-card-cta">Open the care plan →</span>
    </button>
  );
}
