// Care plan: what the family (or centre) keeps together for one senior. Shared with every linked contact.
// Appointments, questions for the doctor (they go onto the GP brief), to-dos with an owner each, the senior's
// medicines and refill reports, and an emergency card. None of it changes what CareLoop's rules decide.
import { useCallback, useEffect, useState } from 'react';
import type { Appointment, CareNotes, Task } from '../shared/contract';
import { briefPdfUrl, getCareNotes, putCareNotes } from '../shared/api';
import { useInsights } from './Health';
import { useRefreshTick } from './live';

const uid = () => Math.random().toString(36).slice(2, 10);
const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { weekday: 'short', day: 'numeric', month: 'short' });
const daysUntil = (d: string, today: string) => Math.round((new Date(d).getTime() - new Date(today).getTime()) / 86400000);

export function useCareNotes(seniorId: string, contactId: string) {
  const [notes, setNotes] = useState<CareNotes | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tick = useRefreshTick();
  useEffect(() => {
    getCareNotes(seniorId, contactId).then(setNotes, (e: Error) => setError(e.message));
  }, [seniorId, contactId, tick]);
  const save = useCallback(
    async (next: CareNotes) => {
      setNotes(next); // show it straight away; the server's copy replaces it
      try {
        setNotes(await putCareNotes(seniorId, contactId, next));
        setError(null);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [seniorId, contactId],
  );
  return { notes, save, error };
}

const QUICK_TASKS = ['Collect the medicine refill', 'Book a polyclinic slot', 'Visit this weekend', 'Check the BP monitor batteries'];

interface Props {
  seniorId: string;
  contactId: string;
  me: string;
  name: string; // the senior
  today: string;
}

export default function CarePlan({ seniorId, contactId, me, name, today }: Props) {
  const { notes, save, error } = useCareNotes(seniorId, contactId);
  const { data: insights } = useInsights(seniorId, contactId);
  if (!notes) return <p className="care-muted">{error ? `Couldn't load the care plan. ${error}` : 'Loading…'}</p>;
  const set = (patch: Partial<CareNotes>) => save({ ...notes, ...patch });

  return (
    <>
      {error && <p className="care-error">Not saved: {error}</p>}
      {notes.updated_by && notes.updated_at && (
        <p className="care-muted plan-updated">
          Last changed by {notes.updated_by}, {new Date(notes.updated_at).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}. Everyone linked to {name} sees this plan.
        </p>
      )}
      <Appointments notes={notes} set={set} today={today} me={me} />
      <Questions notes={notes} set={set} me={me} seniorId={seniorId} />
      <Tasks notes={notes} set={set} me={me} today={today} />
      <Medicines insights={insights ?? null} />
      <EmergencyCard notes={notes} set={set} name={name} />
    </>
  );
}

type SetFn = (patch: Partial<CareNotes>) => void;

function Appointments({ notes, set, today, me }: { notes: CareNotes; set: SetFn; today: string; me: string }) {
  const [adding, setAdding] = useState(false);
  const [d, setD] = useState<Appointment>({ id: '', date: today, time: '', place: '', purpose: '', who_goes: '', notes_after: '' });
  const sorted = [...notes.appointments].sort((a, b) => a.date.localeCompare(b.date));
  const next = sorted.filter((a) => a.date >= today);
  const past = sorted.filter((a) => a.date < today).reverse().slice(0, 3);
  const add = () => {
    set({ appointments: [...notes.appointments, { ...d, id: uid(), time: d.time || null, who_goes: d.who_goes || null }] });
    setAdding(false);
  };
  const update = (id: string, patch: Partial<Appointment>) =>
    set({ appointments: notes.appointments.map((a) => (a.id === id ? { ...a, ...patch } : a)) });
  return (
    <section className="care-card">
      <div className="card-head">
        <h2>Appointments</h2>
        {!adding && (
          <button className="care-link" onClick={() => setAdding(true)}>
            + Add
          </button>
        )}
      </div>
      {next.length === 0 && !adding && <p className="care-muted">No upcoming visit. Add one so everyone knows, and so the GP brief can show it.</p>}
      {next.map((a, i) => (
        <div key={a.id} className={`appt ${i === 0 ? 'is-next' : ''}`}>
          <div className="appt-date">
            <strong>{fmt(a.date)}</strong>
            <span>{daysUntil(a.date, today) === 0 ? 'today' : `in ${daysUntil(a.date, today)} days`}</span>
          </div>
          <div className="appt-body">
            <strong>{a.purpose || 'Visit'}</strong>
            <span className="care-muted">
              {[a.time, a.place].filter(Boolean).join(' · ')}
            </span>
            <span className="appt-who">
              {a.who_goes ? `${a.who_goes} is going` : 'Nobody has said they are going.'}{' '}
              {a.who_goes !== me && (
                <button className="care-link" onClick={() => update(a.id, { who_goes: me })}>
                  I'll go
                </button>
              )}
            </span>
          </div>
          <button className="care-link plan-remove" aria-label="Remove appointment" onClick={() => set({ appointments: notes.appointments.filter((x) => x.id !== a.id) })}>
            ✕
          </button>
        </div>
      ))}
      {adding && (
        <div className="aac-form plan-form">
          <div className="aac-form-row">
            <label>
              Date
              <input type="date" value={d.date} onChange={(e) => setD({ ...d, date: e.target.value })} />
            </label>
            <label>
              Time
              <input value={d.time ?? ''} placeholder="9:30am" onChange={(e) => setD({ ...d, time: e.target.value })} />
            </label>
          </div>
          <label>
            Where
            <input value={d.place} placeholder="e.g. Ang Mo Kio Polyclinic" onChange={(e) => setD({ ...d, place: e.target.value })} />
          </label>
          <label>
            What for
            <input value={d.purpose} placeholder="e.g. Blood pressure review" onChange={(e) => setD({ ...d, purpose: e.target.value })} />
          </label>
          <button className="care-primary" disabled={!d.date} onClick={add}>
            Save appointment
          </button>
          <button className="care-link" onClick={() => setAdding(false)}>
            Cancel
          </button>
        </div>
      )}
      {past.length > 0 && (
        <details className="plan-past">
          <summary>Past visits and what the doctor said</summary>
          {past.map((a) => (
            <label key={a.id} className="plan-after">
              <span>
                {fmt(a.date)} · {a.purpose || 'Visit'}
              </span>
              <textarea
                defaultValue={a.notes_after}
                placeholder="What the doctor said, any medicine changes, the next step"
                onBlur={(e) => e.target.value !== a.notes_after && update(a.id, { notes_after: e.target.value })}
              />
            </label>
          ))}
        </details>
      )}
    </section>
  );
}

function Questions({ notes, set, me, seniorId }: { notes: CareNotes; set: SetFn; me: string; seniorId: string }) {
  const [text, setText] = useState('');
  const open = notes.questions.filter((q) => !q.asked);
  const asked = notes.questions.filter((q) => q.asked);
  const pdf = briefPdfUrl(seniorId);
  const add = () => {
    if (!text.trim()) return;
    set({ questions: [...notes.questions, { id: uid(), text: text.trim(), by: me, added: new Date().toISOString().slice(0, 10), asked: false, answer: '' }] });
    setText('');
  };
  return (
    <section className="care-card">
      <h2>Questions for the doctor</h2>
      <p className="care-muted">Open questions are printed on the GP brief. Pick the three or four that matter most.</p>
      <ul className="plan-list">
        {open.map((q) => (
          <li key={q.id}>
            <span className="plan-q">{q.text}</span>
            <span className="care-muted plan-by">{q.by}</span>
            <button className="care-link" onClick={() => set({ questions: notes.questions.map((x) => (x.id === q.id ? { ...x, asked: true } : x)) })}>
              Asked
            </button>
          </li>
        ))}
      </ul>
      <div className="plan-add">
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} placeholder="e.g. Is the pill timing right?" aria-label="New question" />
        <button className="care-secondary" onClick={add} disabled={!text.trim()}>
          Add
        </button>
      </div>
      {asked.length > 0 && <p className="care-muted">{asked.length} already asked.</p>}
      {pdf && open.length > 0 && (
        <a className="care-link" href={pdf} target="_blank" rel="noreferrer">
          See them on the GP brief →
        </a>
      )}
    </section>
  );
}

function Tasks({ notes, set, me, today }: { notes: CareNotes; set: SetFn; me: string; today: string }) {
  const [title, setTitle] = useState('');
  const open = notes.tasks.filter((t) => !t.done);
  const done = notes.tasks.filter((t) => t.done).slice(-3);
  const add = (t: string) => {
    if (!t.trim()) return;
    set({ tasks: [...notes.tasks, { id: uid(), title: t.trim(), owner: null, done: false, due: null, done_by: null }] });
    setTitle('');
  };
  const update = (id: string, patch: Partial<Task>) => set({ tasks: notes.tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)) });
  const counts = notes.tasks.reduce<Record<string, number>>((acc, t) => {
    if (t.owner) acc[t.owner] = (acc[t.owner] ?? 0) + 1;
    return acc;
  }, {});
  return (
    <section className="care-card">
      <div className="card-head">
        <h2>Shared to-dos</h2>
        {Object.keys(counts).length > 1 && (
          <span className="care-muted">{Object.entries(counts).map(([who, n]) => `${who} ${n}`).join(' · ')}</span>
        )}
      </div>
      {open.length === 0 && <p className="care-muted">Nothing open. Add what needs doing so it isn't all on one person.</p>}
      <ul className="plan-list">
        {open.map((t) => (
          <li key={t.id}>
            <input type="checkbox" aria-label={`Done: ${t.title}`} onChange={() => update(t.id, { done: true, done_by: me })} />
            <span className="plan-q">
              {t.title}
              {t.due && <span className={`plan-due ${t.due < today ? 'is-late' : ''}`}> · by {fmt(t.due)}</span>}
            </span>
            {t.owner ? (
              <span className={`owner-chip ${t.owner === me ? 'is-me' : ''}`}>{t.owner === me ? 'You' : t.owner}</span>
            ) : (
              <button className="care-link" onClick={() => update(t.id, { owner: me })}>
                I'll do it
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className="plan-add">
        <input value={title} onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add(title)} placeholder="Add a to-do" aria-label="New to-do" />
        <button className="care-secondary" onClick={() => add(title)} disabled={!title.trim()}>
          Add
        </button>
      </div>
      <div className="quick-chips">
        {QUICK_TASKS.filter((q) => !open.some((t) => t.title === q)).map((q) => (
          <button key={q} className="chip" onClick={() => add(q)}>
            + {q}
          </button>
        ))}
      </div>
      {done.length > 0 && (
        <p className="care-muted">
          Done lately: {done.map((t) => `${t.title} (${t.done_by ?? 'someone'})`).join('; ')}.
        </p>
      )}
    </section>
  );
}

function Medicines({ insights }: { insights: ReturnType<typeof useInsights>['data'] | null }) {
  if (!insights) return null;
  const low = insights.running_low[insights.running_low.length - 1];
  return (
    <section className="care-card">
      <h2>Medicines</h2>
      {insights.medicines.length === 0 ? (
        <p className="care-muted">No medicines recorded yet. They're set up with the senior app.</p>
      ) : (
        <ul className="plan-list">
          {insights.medicines.map((m) => (
            <li key={m.name}>
              <span className="plan-q">
                <strong>{m.name.charAt(0).toUpperCase() + m.name.slice(1)}</strong> · {m.dose_text}
                <span className="care-muted"> · {m.schedule.join(', ')} · since {fmt(m.started)}</span>
              </span>
              {m.for_bp && <span className="owner-chip">BP</span>}
            </li>
          ))}
        </ul>
      )}
      {low && (
        <p className="care-notice">
          Said a medicine was running low on {fmt(low.date)}. Check the refill is collected (add a to-do above).
        </p>
      )}
      <p className="care-muted">
        Taken on {insights.adherence.taken_days} of {insights.adherence.reported_days} reported days. Doses are as on the label; CareLoop never changes them.
      </p>
    </section>
  );
}

function EmergencyCard({ notes, set, name }: { notes: CareNotes; set: SetFn; name: string }) {
  const [editing, setEditing] = useState(false);
  const [e, setE] = useState(notes.emergency);
  useEffect(() => setE(notes.emergency), [notes.emergency]);
  const filled = Object.values(notes.emergency).some(Boolean);
  return (
    <section className="care-card emergency">
      <div className="card-head">
        <h2>Emergency card</h2>
        <button className="care-link" onClick={() => (editing ? (set({ emergency: e }), setEditing(false)) : setEditing(true))}>
          {editing ? 'Save' : filled ? 'Edit' : 'Fill in'}
        </button>
      </div>
      {editing ? (
        <div className="aac-form">
          {(
            [
              ['allergies', 'Allergies', 'e.g. Penicillin'],
              ['gp_name', 'Family doctor', 'Clinic name'],
              ['gp_phone', "Doctor's phone", '6xxx xxxx'],
              ['home_address', 'Home address', 'Block, street, unit'],
              ['notes', 'Anything else', 'e.g. key with the neighbour at #05-12'],
            ] as const
          ).map(([k, label, ph]) => (
            <label key={k}>
              {label}
              <input value={e[k]} placeholder={ph} onChange={(ev) => setE({ ...e, [k]: ev.target.value })} />
            </label>
          ))}
        </div>
      ) : filled ? (
        <dl className="emergency-dl">
          {notes.emergency.allergies && (<><dt>Allergies</dt><dd>{notes.emergency.allergies}</dd></>)}
          {notes.emergency.gp_name && (<><dt>Family doctor</dt><dd>{notes.emergency.gp_name}{notes.emergency.gp_phone && <> · <a href={`tel:${notes.emergency.gp_phone.replace(/\s/g, '')}`}>{notes.emergency.gp_phone}</a></>}</dd></>)}
          {notes.emergency.home_address && (<><dt>Home</dt><dd>{notes.emergency.home_address}</dd></>)}
          {notes.emergency.notes && (<><dt>Notes</dt><dd>{notes.emergency.notes}</dd></>)}
        </dl>
      ) : (
        <p className="care-muted">What a paramedic or a neighbour would need about {name}. Show it on screen in an emergency.</p>
      )}
      <a className="care-primary is-alert" href="tel:995">
        Emergency: dial 995
      </a>
    </section>
  );
}
