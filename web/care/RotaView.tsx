// Rota management: see who's on duty, the 2-week schedule, and edit the rotation.
// Lives in the Settings (You) tab of the family app.
import { useState, useCallback } from 'react';
import type { FamilyView, RotaView } from '../shared/contract';
import { getRota, putRota, swapRota, deleteRota } from '../shared/api';
import { useLive } from './live';

interface ContactRef { id: string; name: string }

/** Compute the on-duty contact for a given day, mirroring the backend on_duty() logic. */
function dutyFor(rota: RotaView['rota'], contacts: ContactRef[], day: string): ContactRef | null {
  if (!rota || rota.order.length === 0) return null;
  const start = new Date(rota.start_date + 'T00:00:00');
  const d = new Date(day + 'T00:00:00');
  const daysSince = Math.floor((d.getTime() - start.getTime()) / 86400000);
  if (daysSince < 0) return null;
  // Swap wins for the exact date.
  const swap = rota.swaps.find(s => s.date === day);
  if (swap) {
    const c = contacts.find(c => c.id === swap.contact_id);
    if (c) return c;
    return null;
  }
  // Filter the order to valid contacts.
  const valid = rota.order.map(id => contacts.find(c => c.id === id)).filter(Boolean) as ContactRef[];
  if (valid.length === 0) return null;
  const idx = rota.mode === 'weekly'
    ? Math.floor(daysSince / 7) % valid.length
    : daysSince % valid.length;
  return valid[idx];
}

function fmt(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function addDays(base: string, n: number): string {
  const d = new Date(base + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return fmt(d);
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function RotaView({ view }: { view: FamilyView }) {
  const contacts: ContactRef[] = [
    { id: view.contact.id, name: view.contact.name },
    ...view.other_contacts,
  ];
  const [rotaView, setRotaView] = useState<RotaView | null>(null);
  const [editing, setEditing] = useState(false);
  const [swapping, setSwapping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getRota(view.senior.id).then(
      (r) => { setRotaView(r); setError(null); },
      (e: Error) => setError(e.message),
    );
  }, [view.senior.id]);
  useLive(load);

  if (error && !rotaView) return (
    <section className="care-card">
      <h2>Rota</h2>
      <p className="care-error">{error}</p>
      <button className="care-secondary" onClick={load}>Try again</button>
    </section>
  );
  if (!rotaView) return (
    <section className="care-card">
      <h2>Rota</h2>
      <p className="care-muted" role="status">Loading rota…</p>
    </section>
  );

  const rota = rotaView.rota;
  const today = view.today;
  const hasRota = rota !== null && rota.order.length > 0;

  // Build a 14-day schedule starting from today.
  const schedule = Array.from({ length: 14 }, (_, i) => {
    const day = addDays(today, i);
    const duty = dutyFor(rota, contacts, day);
    const isToday = i === 0;
    return { day, duty, isToday };
  });

  return (
    <section className="care-card">
      <h2>Who's on duty</h2>

      {hasRota ? (
        <>
          <p className="care-muted">
            Today: <strong>{rotaView.on_duty?.name ?? 'Nobody'}</strong>
            {rotaView.on_duty?.id === view.contact.id && ' (you)'}
          </p>

          {/* 2-week schedule grid */}
          <div className="rota-grid">
            {schedule.map(({ day, duty, isToday }) => (
              <div key={day} className={`rota-day ${isToday ? 'is-today' : ''}`}>
                <span className="rota-dow">{DOW[new Date(day + 'T00:00:00').getDay()]}</span>
                <span className="rota-date">{day.slice(8)}</span>
                <span className={`rota-name ${duty?.id === view.contact.id ? 'is-me' : ''}`}>
                  {duty?.name.split(' ')[0] ?? '—'}
                </span>
              </div>
            ))}
          </div>

          <div className="rota-actions">
            <button className="care-secondary" onClick={() => setEditing(e => !e)}>
              {editing ? 'Close' : 'Edit rotation'}
            </button>
            <button className="care-secondary" onClick={() => setSwapping(s => !s)}>
              {swapping ? 'Close' : 'Swap a day'}
            </button>
            <button className="care-secondary" onClick={async () => {
              await deleteRota(view.senior.id);
              load();
            }}>
              Remove rota
            </button>
          </div>

          {editing && (
            <RotaEditor
              rota={rota!}
              contacts={contacts}
              onSave={async (mode, startDate, order) => {
                await putRota(view.senior.id, mode, startDate, order);
                setEditing(false);
                load();
              }}
            />
          )}

          {swapping && (
            <SwapEditor
              contacts={contacts}
              today={today}
              onSwap={async (date, contactId) => {
                await swapRota(view.senior.id, date, contactId);
                load();
              }}
            />
          )}
        </>
      ) : (
        <>
          <p className="care-muted">
            No rota set. Handovers go to the primary caregiver.
            {contacts.length > 1 && ' Set up a rota so siblings can take turns.'}
          </p>
          {contacts.length > 1 && (
            <button className="care-primary" onClick={() => setEditing(true)}>
              Set up a rota
            </button>
          )}
          {editing && (
            <RotaEditor
              rota={null}
              contacts={contacts}
              onSave={async (mode, startDate, order) => {
                await putRota(view.senior.id, mode, startDate, order);
                setEditing(false);
                load();
              }}
            />
          )}
        </>
      )}
    </section>
  );
}

function RotaEditor({ rota, contacts, onSave }: {
  rota: RotaView['rota'];
  contacts: ContactRef[];
  onSave: (mode: 'weekly' | 'daily', startDate: string, order: string[]) => Promise<void>;
}) {
  const [mode, setMode] = useState<'weekly' | 'daily'>(rota?.mode ?? 'weekly');
  const [startDate, setStartDate] = useState(rota?.start_date ?? new Date().toISOString().slice(0, 10));
  // Default: all contacts in their natural order.
  const [order, setOrder] = useState<string[]>(rota?.order ?? contacts.map(c => c.id));
  const [busy, setBusy] = useState(false);

  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= order.length) return;
    const next = [...order];
    [next[i], next[j]] = [next[j], next[i]];
    setOrder(next);
  };

  return (
    <div className="rota-editor">
      <label>
        Rotation
        <select value={mode} onChange={e => setMode(e.target.value as 'weekly' | 'daily')}>
          <option value="weekly">Weekly (7 days each)</option>
          <option value="daily">Daily (rotates every day)</option>
        </select>
      </label>
      <label>
        Start date
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
      </label>
      <div className="rota-order">
        <p className="care-muted">Order (drag-free: use arrows):</p>
        {order.map((id, i) => {
          const c = contacts.find(c => c.id === id);
          return (
            <div key={id} className="rota-order-item">
              <span>{i + 1}. {c?.name ?? id}</span>
              <button type="button" onClick={() => move(i, -1)} disabled={i === 0}>↑</button>
              <button type="button" onClick={() => move(i, 1)} disabled={i === order.length - 1}>↓</button>
            </div>
          );
        })}
      </div>
      <button
        className="care-primary"
        disabled={busy || order.length === 0}
        onClick={async () => {
          setBusy(true);
          try { await onSave(mode, startDate, order); } finally { setBusy(false); }
        }}
      >
        {busy ? 'Saving…' : 'Save rota'}
      </button>
    </div>
  );
}

function SwapEditor({ contacts, today, onSwap }: {
  contacts: ContactRef[];
  today: string;
  onSwap: (date: string, contactId: string) => Promise<void>;
}) {
  const [date, setDate] = useState(today);
  const [contactId, setContactId] = useState(contacts[0]?.id ?? '');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  return (
    <div className="rota-editor">
      <p className="care-muted">Swap: pick a date and who covers it. This overrides the rotation for that one day only.</p>
      <label>
        Date
        <input type="date" value={date} onChange={e => { setDate(e.target.value); setDone(false); }} />
      </label>
      <label>
        Who covers this day
        <select value={contactId} onChange={e => { setContactId(e.target.value); setDone(false); }}>
          {contacts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <button
        className="care-primary"
        disabled={busy || !contactId}
        onClick={async () => {
          setBusy(true);
          try {
            await onSwap(date, contactId);
            setDone(true);
          } finally { setBusy(false); }
        }}
      >
        {busy ? 'Saving…' : done ? 'Saved ✓' : 'Add swap'}
      </button>
    </div>
  );
}
