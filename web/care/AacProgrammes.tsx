// Weekly programme timetable (GET/PUT /aac/{aac_id}/programmes). Staff enter it once; it feeds every
// linked senior's suggestions.
import { useEffect, useState } from 'react';
import type { Programme, ProgrammeIn, Weekday } from '../shared/contract';
import { getProgrammes, putProgrammes } from '../shared/api';
import { BackLink } from './HandoverView';

const DAYS: { id: Weekday; label: string }[] = [
  { id: 'mon', label: 'Mon' },
  { id: 'tue', label: 'Tue' },
  { id: 'wed', label: 'Wed' },
  { id: 'thu', label: 'Thu' },
  { id: 'fri', label: 'Fri' },
  { id: 'sat', label: 'Sat' },
  { id: 'sun', label: 'Sun' },
];

const strip = ({ title, title_zh, weekdays, time, tags, indoor, free }: Programme): ProgrammeIn => ({
  title, title_zh, weekdays, time, tags, indoor, free,
});

const blank = { title: '', weekdays: [] as Weekday[], time: '10:00', indoor: true, free: true };

export default function AacProgrammes({ centre }: { centre: { id: string; name: string } }) {
  const [list, setList] = useState<Programme[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState(blank);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getProgrammes(centre.id).then(setList, (e: Error) => setError(e.message));
  }, [centre.id]);

  const save = async (next: ProgrammeIn[]) => {
    setBusy(true);
    setError(null);
    try {
      setList(await putProgrammes(centre.id, next));
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const add = async () => {
    if (!list || !draft.title.trim() || !draft.weekdays.length) return;
    const ok = await save([...list.map(strip), { ...draft, title: draft.title.trim(), tags: [] }]);
    if (ok) {
      setDraft(blank);
      setAdding(false);
    }
  };

  const remove = (p: Programme) => list && save(list.filter((x) => x.id !== p.id).map(strip));
  const toggleDay = (d: Weekday) =>
    setDraft((cur) => ({ ...cur, weekdays: cur.weekdays.includes(d) ? cur.weekdays.filter((x) => x !== d) : [...cur.weekdays, d] }));

  return (
    <>
      <BackLink to="/care/aac" label="Caseload" />
      <h1>Weekly programmes</h1>
      <p className="care-lead">
        Enter {centre.name}'s timetable once. CareLoop suggests these to linked seniors who'd enjoy them, indoor ones first
        on rainy or hazy days.
      </p>
      {error && <p className="care-error">{error}</p>}
      {!list && !error && <p className="care-muted">Loading…</p>}
      {list?.some((p) => p.sample) && <p className="care-notice">These are sample programmes for the demo. Replace them with your centre's.</p>}
      {list && !list.length && <p className="care-muted">No programmes yet.</p>}

      {list &&
        DAYS.map(({ id, label }) => {
          const items = list.filter((p) => p.weekdays.includes(id)).sort((a, b) => a.time.localeCompare(b.time));
          if (!items.length) return null;
          return (
            <section key={id} className="care-card aac-day">
              <h2>{label}</h2>
              <ul className="aac-programmes">
                {items.map((p) => (
                  <li key={p.id}>
                    <span className="aac-prog-time">{p.time}</span>
                    <span className="aac-prog-body">
                      <strong>{p.title}</strong>
                      <span className="care-muted">
                        {p.indoor ? 'Indoor' : 'Outdoor'} · {p.free ? 'Free' : 'Small fee'}
                        {p.sample && ' · Sample'}
                      </span>
                    </span>
                    <button className="care-link aac-remove" disabled={busy} onClick={() => remove(p)} aria-label={`Remove ${p.title}`}>
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}

      {adding ? (
        <section className="care-card aac-form">
          <h2>Add a programme</h2>
          <label>
            Name
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="e.g. Line dancing" />
          </label>
          <fieldset className="aac-days">
            <legend>Days</legend>
            {DAYS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className={`aac-day-chip ${draft.weekdays.includes(id) ? 'is-on' : ''}`}
                aria-pressed={draft.weekdays.includes(id)}
                onClick={() => toggleDay(id)}
              >
                {label}
              </button>
            ))}
          </fieldset>
          <label>
            Starts
            <input type="time" value={draft.time} onChange={(e) => setDraft({ ...draft, time: e.target.value })} />
          </label>
          <label className="aac-check">
            <input type="checkbox" checked={draft.indoor} onChange={(e) => setDraft({ ...draft, indoor: e.target.checked })} />
            Indoors
          </label>
          <label className="aac-check">
            <input type="checkbox" checked={draft.free} onChange={(e) => setDraft({ ...draft, free: e.target.checked })} />
            Free
          </label>
          <button className="care-primary" disabled={!draft.title.trim() || !draft.weekdays.length || busy} onClick={add}>
            {busy ? 'Saving…' : 'Add to timetable'}
          </button>
          <button className="care-link" onClick={() => setAdding(false)}>
            Cancel
          </button>
        </section>
      ) : (
        list && (
          <button className="care-secondary" onClick={() => setAdding(true)}>
            Add a programme
          </button>
        )
      )}
    </>
  );
}
