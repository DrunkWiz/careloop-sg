// Weekly programme timetable. Staff enter it once; it feeds linked seniors' suggestions.
import { useState } from 'react';
import type { Contact, Programme } from '../shared/contract';
import { saveProgrammes } from '../shared/api';
import { navigate } from './nav';

const DAYS: Programme['day'][] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface Props {
  contact: Contact;
  centre: string;
  initial: Programme[];
}

export default function AacProgrammes({ contact, centre, initial }: Props) {
  const [list, setList] = useState<Programme[]>(initial);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ day: 'Mon' as Programme['day'], start: '10:00', title: '', place: '', indoor: true });

  const persist = async (next: Programme[]) => setList(await saveProgrammes(contact.id, next));

  const add = async () => {
    if (!draft.title.trim()) return;
    await persist([...list, { ...draft, id: `p-${Date.now()}`, title: draft.title.trim(), place: draft.place.trim(), sample: false }]);
    setDraft({ ...draft, title: '', place: '' });
    setAdding(false);
  };

  const remove = (id: string) => persist(list.filter((p) => p.id !== id));
  const hasSamples = list.some((p) => p.sample);

  return (
    <>
      <button className="care-link care-back" onClick={() => navigate('/care/aac')}>
        ← Caseload
      </button>
      <h1>Weekly programmes</h1>
      <p className="care-lead">
        Enter {centre}'s timetable once. CareLoop suggests these to linked seniors who'd enjoy them, indoor ones first on
        rainy or hazy days.
      </p>
      {hasSamples && <p className="care-notice">Sample programmes for the demo. Replace them with your centre's.</p>}

      {DAYS.map((day) => {
        const items = list.filter((p) => p.day === day).sort((a, b) => a.start.localeCompare(b.start));
        if (!items.length) return null;
        return (
          <section key={day} className="care-card aac-day">
            <h2>{day}</h2>
            <ul className="aac-programmes">
              {items.map((p) => (
                <li key={p.id}>
                  <span className="aac-prog-time">{p.start}</span>
                  <span className="aac-prog-body">
                    <strong>{p.title}</strong>
                    <span className="care-muted">
                      {p.place}
                      {p.place && ' · '}
                      {p.indoor ? 'Indoor' : 'Outdoor'}
                      {p.sample && ' · Sample'}
                    </span>
                  </span>
                  <button className="care-link aac-remove" onClick={() => remove(p.id)} aria-label={`Remove ${p.title}`}>
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
          <div className="aac-form-row">
            <label>
              Day
              <select value={draft.day} onChange={(e) => setDraft({ ...draft, day: e.target.value as Programme['day'] })}>
                {DAYS.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </label>
            <label>
              Starts
              <input type="time" value={draft.start} onChange={(e) => setDraft({ ...draft, start: e.target.value })} />
            </label>
          </div>
          <label>
            Where
            <input value={draft.place} onChange={(e) => setDraft({ ...draft, place: e.target.value })} placeholder="e.g. Activity room" />
          </label>
          <label className="aac-check">
            <input type="checkbox" checked={draft.indoor} onChange={(e) => setDraft({ ...draft, indoor: e.target.checked })} />
            Indoors
          </label>
          <button className="care-primary" disabled={!draft.title.trim()} onClick={add}>
            Add to timetable
          </button>
          <button className="care-link" onClick={() => setAdding(false)}>
            Cancel
          </button>
        </section>
      ) : (
        <button className="care-secondary" onClick={() => setAdding(true)}>
          Add a programme
        </button>
      )}
    </>
  );
}
