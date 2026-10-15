// Bring in a centre's timetable from what it already keeps: a calendar file or link (.ics, from Google
// Calendar or Outlook) or a spreadsheet (.csv). CareLoop shows what it read, with its guesses, before
// anything is saved. A calendar link is pulled again once a day, so changes reach seniors on their own.
import { useEffect, useState } from 'react';
import type { ProgrammeFeed, TimetableImport as Result } from '../shared/contract';
import { getProgrammeFeed, importTimetable, stopProgrammeFeed, usingMocks } from '../shared/api';

const DAY = { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' } as const;
const TEMPLATE = 'Programme,中文,Days,Time,Indoor/Outdoor,Fee\nMorning exercise,早操,"Mon, Wed, Fri",8:30am,Indoor,Free\nKaraoke,卡拉OK,Sat,10am,Indoor,Free\n';
const when = (d: string) => new Date(d).toLocaleString('en-SG', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

export default function TimetableImport({ aacId, onSaved }: { aacId: string; onSaved: () => void }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<{ text?: string; url?: string; label: string } | null>(null);
  const [link, setLink] = useState('');
  const [preview, setPreview] = useState<Result | null>(null);
  const [feed, setFeed] = useState<ProgrammeFeed | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProgrammeFeed(aacId).then(setFeed, () => setFeed(null));
  }, [aacId]);

  const check = async (src: { text?: string; url?: string; label: string }) => {
    setBusy(true);
    setError(null);
    setPreview(null);
    setSource(src);
    try {
      setPreview(await importTimetable(aacId, { text: src.text, url: src.url }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!source) return;
    setBusy(true);
    try {
      const r = await importTimetable(aacId, { text: source.text, url: source.url, save: true });
      setFeed(r.feed);
      setPreview(null);
      setSource(null);
      setOpen(false);
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onFile = async (f: File | undefined) => {
    if (f) await check({ text: await f.text(), label: f.name });
  };

  return (
    <section className="care-card tti">
      <div className="card-head">
        <h2>Bring in your timetable</h2>
        {!open && (
          <button className="care-link" onClick={() => setOpen(true)}>
            Import…
          </button>
        )}
      </div>
      {feed && feed.url && (
        <p className="care-muted">
          Pulled from your calendar link {feed.error ? `(last try failed: ${feed.error}) ` : ''}on {when(feed.pulled_at)}: {feed.count} programmes.
          CareLoop pulls it again every day.{' '}
          <button className="care-link" onClick={() => void stopProgrammeFeed(aacId).then(() => setFeed(null))}>
            Stop
          </button>
        </p>
      )}
      {!open && !feed?.url && (
        <p className="care-muted">Already keep it in Google Calendar, Outlook or a spreadsheet? Import it instead of typing it in.</p>
      )}
      {open && (
        <>
          {usingMocks && <p className="care-notice">Importing needs the API: run npm run dev:live.</p>}
          <div className="tti-ways">
            <label className="tti-way">
              <strong>A file</strong>
              <span className="care-muted">Calendar (.ics) or spreadsheet (.csv)</span>
              <input type="file" accept=".ics,.csv,text/calendar,text/csv" disabled={busy || usingMocks} onChange={(e) => void onFile(e.target.files?.[0])} />
            </label>
            <form
              className="tti-way"
              onSubmit={(e) => {
                e.preventDefault();
                if (link.trim()) void check({ url: link.trim(), label: 'your calendar link' });
              }}
            >
              <strong>A calendar link</strong>
              <span className="care-muted">The “public address in iCal format” from Google Calendar, or Outlook's ICS link. Pulled again daily.</span>
              <span className="tti-link">
                <input type="url" placeholder="https://calendar.google.com/…/basic.ics" value={link} onChange={(e) => setLink(e.target.value)} disabled={busy || usingMocks} />
                <button className="care-secondary" disabled={busy || usingMocks || !link.trim()}>Check</button>
              </span>
            </form>
          </div>
          <p className="care-muted">
            A spreadsheet needs columns for the programme, the days and the time.{' '}
            <a className="care-link" href={`data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`} download="timetable-template.csv">
              Download a template
            </a>
          </p>
          {busy && <p className="care-muted">Reading…</p>}
          {error && <p className="care-error">{error}</p>}
          {preview && (
            <div className="tti-preview">
              <h3>
                From {source?.label}: {preview.programmes.length} weekly programme{preview.programmes.length === 1 ? '' : 's'}
              </h3>
              {preview.programmes.length > 0 && (
                <ul className="tti-list">
                  {preview.programmes.map((p) => (
                    <li key={`${p.title}-${p.time}`}>
                      <strong>{p.title}</strong>
                      {p.title_zh && <span> {p.title_zh}</span>}
                      <span className="care-muted">
                        {' '}
                        · {p.weekdays.map((d) => DAY[d]).join(', ')} {p.time} · {p.indoor ? 'Indoor' : 'Outdoor'} · {p.free ? 'Free' : 'Small fee'}
                      </span>
                      {p.tags.length > 0 && <span className="tti-tags">Matches seniors who like: {p.tags.join(', ')}</span>}
                    </li>
                  ))}
                </ul>
              )}
              {preview.warnings.length > 0 && (
                <ul className="tti-warnings">
                  {preview.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
              <p className="care-muted">Indoor, fee and “likes” are guessed from each title. Check them; you can change any programme after.</p>
              <div className="tti-actions">
                <button className="care-primary" disabled={busy || !preview.programmes.length} onClick={() => void save()}>
                  Use this timetable
                </button>
                <span className="care-muted">Replaces the current one.</span>
              </div>
            </div>
          )}
          <button
            className="care-link"
            onClick={() => {
              setOpen(false);
              setPreview(null);
              setError(null);
            }}
          >
            Close
          </button>
        </>
      )}
    </section>
  );
}
