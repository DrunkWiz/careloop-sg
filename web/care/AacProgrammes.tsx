// Weekly programme timetable (GET/PUT /aac/{aac_id}/programmes). Staff enter it once; it feeds every
// linked senior's suggestions.
import { useEffect, useState } from 'react';
import type { Activities, CaseloadRow, Programme, ProgrammeIn, Weekday } from '../shared/contract';
import { getActivities, getProgrammes, putProgrammes } from '../shared/api';
import { BackLink } from './HandoverView';
import { timeKey } from './ActivitiesView';
import TimetableImport from './TimetableImport';

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

// Which seniors each programme suits, from what they told CareLoop they like (the same match the
// engine's suggestions use). Matched by title, so it works for entered and sample timetables alike.
function useSuits(seniors: CaseloadRow[], timetable: string) {
  const [acts, setActs] = useState<{ name: string; a: Activities }[]>([]);
  // Refetch when the caseload's members change, not on every 15-second refresh.
  const key = seniors.map((r) => `${r.senior.id}:${r.contact_id}`).join(',') + '|' + timetable;
  useEffect(() => {
    Promise.all(seniors.map((r) => getActivities(r.senior.id, r.contact_id).then((a) => ({ name: r.senior.name, a }), () => null))).then(
      (xs) => setActs(xs.filter((x): x is { name: string; a: Activities } => !!x)),
    );
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  const suits = (title: string) =>
    acts.flatMap(({ name, a }) => {
      const p = a.own_aac?.programmes.find((x) => x.title === title);
      return p?.fits ? [{ name, like: p.fits }] : [];
    });
  return { acts, suits };
}

export default function AacProgrammes({ centre, seniors }: { centre: { id: string; name: string }; seniors: CaseloadRow[] }) {
  const [list, setList] = useState<Programme[] | null>(null);
  const { acts, suits } = useSuits(seniors, (list ?? []).map((p) => p.title).join(','));
  const samples = acts.find((x) => x.a.own_aac?.id === centre.id)?.a.own_aac?.programmes.filter((p) => p.sample) ?? [];
  const ccs = acts[0]?.a.nearby_ccs ?? [];
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
        Enter {centre.name}'s timetable once, or import it. CareLoop suggests these to linked seniors who'd enjoy them, indoor ones first
        on rainy or hazy days.
      </p>
      <TimetableImport aacId={centre.id} onSaved={() => void getProgrammes(centre.id).then(setList, (e: Error) => setError(e.message))} />
      {error && <p className="care-error">{error}</p>}
      {!list && !error && <p className="care-muted">Loading…</p>}
      {list?.some((p) => p.sample) && <p className="care-notice">These are sample programmes for the demo. Replace them with your centre's.</p>}
      {list && !list.length && (
        <section className="care-card">
          <p>No timetable entered yet. Seniors are being offered the sample timetable meanwhile.</p>
          {samples.length > 0 && (
            <button
              className="care-secondary"
              disabled={busy}
              onClick={() => save(samples.map(({ title, title_zh, weekdays, time, tags, indoor, free }) => ({ title, title_zh, weekdays, time, tags, indoor, free })))}
            >
              Start from the sample timetable ({samples.length} programmes)
            </button>
          )}
        </section>
      )}

      {list &&
        DAYS.map(({ id, label }) => {
          const items = list.filter((p) => p.weekdays.includes(id)).sort((a, b) => timeKey(a.time) - timeKey(b.time));
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
                      {suits(p.title).length > 0 && (
                        <span className="suits">
                          Suits{' '}
                          {suits(p.title).map((x) => (
                            <span key={x.name} className="suit-chip">
                              {x.name} <em>({x.like})</em>
                            </span>
                          ))}
                        </span>
                      )}
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

      {ccs.length > 0 && (
        <section className="care-card">
          <h2>Community clubs nearby</h2>
          <p className="care-muted">From PA's list on data.gov.sg. CareLoop offers the nearest one when there's nothing at your centre that day.</p>
          <ul className="act-list">
            {ccs.map((c) => (
              <li key={c.id} className="act-item">
                <span className="act-kind is-cc">CC</span>
                <span className="act-body">
                  <strong>{c.name}</strong>
                  <span className="care-muted">{c.km} km · {c.address}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
