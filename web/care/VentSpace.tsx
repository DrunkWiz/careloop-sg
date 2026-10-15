// Vent space: an anonymous room where caregivers can let off steam to each other.
// Not for medical advice. No caregiver_id or senior_id is ever saved with a post.
// The backend strips phone numbers, NRIC and postal codes before saving.
// Owner: Nathan.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { VentPost } from '../shared/contract';
import { getVentFeed, hugVentPost, postVent, reportVentPost } from '../shared/api';
import { useT } from '../shared/i18n';

const NICK_KEY = 'careloop-vent-nick';

function randomNick(): string {
  const n = Math.floor(Math.random() * 999) + 1;
  return `Caregiver ${String(n).padStart(3, '0')}`;
}

function getNick(): string {
  try {
    const s = localStorage.getItem(NICK_KEY);
    if (s) return s;
  } catch { /* ignore */ }
  const n = randomNick();
  try { localStorage.setItem(NICK_KEY, n); } catch { /* ignore */ }
  return n;
}

// Words suggesting someone is in crisis. The post still goes through; we just show a gentle card.
const CRISIS_PATTERNS: string[] = [
  "can't go on", 'cannot go on', 'cant go on',
  'want to die', 'wanna die', 'wish i was dead', 'better off dead',
  'end it all', 'end it', 'end my life',
  'kill myself', 'suicide', 'suicidal',
  'no point living', 'no reason to live',
  "can't take it anymore", 'cannot take it anymore',
  'giving up on life',
  // Chinese
  '不想活', '活不下去', '想死', '不想活了', '了结', '结束生命',
  '不想面对', '撑不下去', '活得很累', '生不如死',
];

function hasCrisis(text: string): boolean {
  const lower = text.toLowerCase();
  return CRISIS_PATTERNS.some((w) => lower.includes(w));
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function VentSpace({ compact = false }: { compact?: boolean }) {
  const t = useT();
  const [posts, setPosts] = useState<VentPost[]>([]);
  const [text, setText] = useState('');
  const [nick, setNick] = useState(getNick);
  const [posting, setPosting] = useState(false);
  const [showCrisis, setShowCrisis] = useState(false);
  const [hugged, setHugged] = useState<Set<string>>(new Set());
  const [reported, setReported] = useState<Set<string>>(new Set());
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const load = useCallback(() => {
    getVentFeed().then(setPosts, () => {});
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, 10000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [load]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || !nick.trim()) return;
    setPosting(true);
    const wasCrisis = hasCrisis(trimmed);
    postVent(nick, trimmed)
      .then((p) => {
        setPosts((prev) => [p, ...prev.filter((x) => x.id !== p.id)]);
        setText('');
        if (wasCrisis) setShowCrisis(true);
      })
      .finally(() => setPosting(false));
  };

  const hug = (id: string) => {
    if (hugged.has(id)) return;
    setHugged((s) => new Set(s).add(id));
    // Optimistic update
    setPosts((prev) => prev.map((x) => (x.id === id ? { ...x, hugs: x.hugs + 1 } : x)));
    hugVentPost(id).then(
      (p) => setPosts((prev) => prev.map((x) => (x.id === p.id ? p : x))),
      () => setHugged((s) => { const n = new Set(s); n.delete(id); return n; }),
    );
  };

  const report = (id: string) => {
    setReported((s) => new Set(s).add(id));
    reportVentPost(id).then(() => {
      setPosts((prev) => prev.filter((x) => x.id !== id));
    });
  };

  const newNick = () => {
    const n = randomNick();
    setNick(n);
    try { localStorage.setItem(NICK_KEY, n); } catch { /* ignore */ }
  };

  const aicUrl = t('vent.crisis.aicUrl');

  return (
    <div className={`vent ${compact ? 'is-compact' : ''}`}>
      <header className="vent-head">
        <h1>{t('vent.title')}</h1>
        <div className="vent-nick">
          <span className="vent-nick-label" aria-label="Your anonymous nickname">{nick}</span>
          <button className="vent-nick-btn" onClick={newNick} aria-label={t('vent.newNick')}>
            {t('vent.newNick')} ↻
          </button>
        </div>
      </header>

      <p className="vent-note">{t('vent.note')}</p>

      {showCrisis && (
        <div className="vent-crisis" role="alert">
          <p className="vent-crisis-title">{t('vent.crisis.title')}</p>
          <p className="vent-crisis-body">{t('vent.crisis.body')}</p>
          <p className="vent-crisis-line">
            <a href="tel:1767" className="vent-crisis-link">{t('vent.crisis.samaritans')}</a>
          </p>
          <p className="vent-crisis-line">
            <a href={aicUrl} target="_blank" rel="noopener noreferrer" className="vent-crisis-link">
              {t('vent.crisis.aic')} ↗
            </a>
          </p>
          <button className="care-secondary vent-crisis-close" onClick={() => setShowCrisis(false)}>
            OK
          </button>
        </div>
      )}

      <div className="vent-compose">
        <textarea
          className="vent-input"
          placeholder={t('vent.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          rows={3}
          aria-label={t('vent.placeholder')}
        />
        <button
          className="vent-post-btn"
          onClick={submit}
          disabled={posting || !text.trim()}
        >
          {t('vent.post')}
        </button>
      </div>

      <div className="vent-feed">
        {posts.length === 0 && <p className="care-muted vent-empty">{t('vent.empty')}</p>}
        {posts.map((p) => (
          <article key={p.id} className="vent-post">
            <div className="vent-post-head">
              <strong className="vent-post-nick">{p.nickname}</strong>
              <span className="vent-post-time">{timeAgo(p.time)}</span>
            </div>
            <p className="vent-post-text">{p.text}</p>
            <div className="vent-post-actions">
              <button
                className={`vent-hug ${hugged.has(p.id) ? 'is-hugged' : ''}`}
                onClick={() => hug(p.id)}
                disabled={hugged.has(p.id)}
                aria-label={t('vent.meToo')}
              >
                <span aria-hidden="true">{'\u2764\uFE0F'}</span> {t('vent.meToo')}
                {p.hugs > 0 && <span className="vent-hug-count">{p.hugs}</span>}
              </button>
              {!reported.has(p.id) ? (
                <button className="vent-report" onClick={() => report(p.id)}>
                  {t('vent.report')}
                </button>
              ) : (
                <span className="vent-reported">{t('vent.reported')}</span>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
