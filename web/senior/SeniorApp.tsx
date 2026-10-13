// The /senior app. Owner: Mingyu.
// Big buttons for the daily things, voice for everything else. It asks; it doesn't report numbers.
import { useCallback, useEffect, useRef, useState } from 'react';
import { LangContext, translate, type Lang, type StringKey } from '../shared/i18n';
import { api, usingMock } from './api';
import { mock } from './mock';
import type { BP, Message, Today } from './types';
import { useHoldToTalk } from './useHoldToTalk';
import { Toast } from './ui';
import { Home } from './screens/Home';
import { Feel } from './screens/Feel';
import { LogBP, type BPEntry } from './screens/LogBP';
import { Confirm } from './screens/Confirm';
import { RedFlag } from './screens/RedFlag';
import { Knows } from './screens/Knows';
import { Pair } from './screens/Pair';
import './senior.css';

type View =
  | { name: 'home' }
  | { name: 'feel' }
  | { name: 'bp'; initial?: Partial<BPEntry> }
  | { name: 'confirm'; bp: BP }
  | { name: 'knows' };

// Per-device conveniences only; the senior's record lives on the server.
const store = {
  get(key: string) { try { return localStorage.getItem(`careloop.${key}`); } catch { return null; } },
  set(key: string, v: string) { try { localStorage.setItem(`careloop.${key}`, v); } catch { /* private mode */ } },
};

export default function SeniorApp() {
  const forcePair = new URLSearchParams(location.search).has('pair');
  const [seniorId, setSeniorId] = useState<string | null>(forcePair ? null : store.get('seniorId'));
  const [lang, setLangState] = useState<Lang>((store.get('lang') as Lang) || 'en');
  const [today, setToday] = useState<Today | null>(null);
  const [view, setView] = useState<View>({ name: 'home' });
  const [redFlag, setRedFlag] = useState<Message | null>(null);
  const [busy, setBusy] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);
  const toastTimer = useRef<number>();

  const t = (key: StringKey, vars?: Record<string, string | number>) => translate(lang, key, vars);

  const toast = useCallback((text: string) => {
    setToastText(text);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastText(null), 3500);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    store.set('lang', l);
  };

  // The mock writes its canned text in the senior's language; keep it in step before fetching.
  useEffect(() => { if (usingMock) mock.setLang(lang); }, [lang]);

  const refresh = useCallback(async () => {
    if (!seniorId) return;
    try {
      setToday(await api.today(seniorId));
    } catch {
      toast(translate(lang, 'common.offline'));
    }
  }, [seniorId, lang, toast]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { document.documentElement.lang = lang === 'zh' ? 'zh-Hans' : 'en-SG'; }, [lang]);

  const checkin = async (text: string, source: 'voice' | 'typed' | 'button', thanks: StringKey = 'checkin.thanks') => {
    if (!seniorId) return;
    setBusy(true);
    try {
      const res = await api.checkin(seniorId, text, lang, source);
      if (res.message?.rung === 'R') {
        setRedFlag(res.message);
      } else {
        const unsure = res.facts.bp.find((b) => b.needs_confirmation);
        if (unsure) {
          setView({ name: 'confirm', bp: unsure });
        } else {
          setView({ name: 'home' });
          toast(res.message?.text || t(thanks));
        }
      }
      refresh();
    } catch {
      toast(t('common.offline'));
    } finally {
      setBusy(false);
    }
  };

  const saveReading = async (bp: BPEntry, source: 'cuff' | 'voice') => {
    if (!seniorId) return;
    setBusy(true);
    try {
      await api.reading(seniorId, bp, source);
      setView({ name: 'home' });
      toast(t('common.saved'));
      refresh();
    } catch {
      toast(t('common.offline'));
    } finally {
      setBusy(false);
    }
  };

  const talk = useHoldToTalk(lang, (text) => checkin(text, 'voice'));

  if (!seniorId) {
    return (
      <LangContext.Provider value={lang}>
        <div className="sa-app">
          <Pair lang={lang} setLang={setLang} onPaired={(r) => {
            store.set('seniorId', r.senior_id);
            setSeniorId(r.senior_id);
            if (forcePair) history.replaceState(null, '', location.pathname);
            toast(translate(lang, 'pair.done', { contact: r.contact_name }));
          }} />
          <Toast text={toastText} />
        </div>
      </LangContext.Provider>
    );
  }

  const prompt = today?.prompt?.text || t('checkin.default');

  return (
    <LangContext.Provider value={lang}>
      <div className="sa-app">
        <header className="sa-top">
          <span className="sa-brand">{t('app.name')}</span>
          <button className="sa-lang" onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}>{t('lang.switch')}</button>
        </header>
        {usingMock && <p className="sa-demo">{t('demo.banner')}</p>}

        {redFlag ? (
          <RedFlag message={redFlag} onClose={() => { setRedFlag(null); setView({ name: 'home' }); }} />
        ) : view.name === 'feel' ? (
          <Feel prompt={prompt} talk={talk} busy={busy} onSend={(text, source) => checkin(text, source)} onBack={() => setView({ name: 'home' })} />
        ) : view.name === 'bp' ? (
          <LogBP initial={view.initial} busy={busy} onSave={(bp) => saveReading(bp, 'cuff')} onBack={() => setView({ name: 'home' })} />
        ) : view.name === 'confirm' ? (
          <Confirm bp={view.bp} busy={busy}
            onYes={() => saveReading({ systolic: view.bp.systolic, diastolic: view.bp.diastolic, pulse: view.bp.pulse }, 'voice')}
            onNo={() => setView({ name: 'bp', initial: { systolic: view.bp.systolic, diastolic: view.bp.diastolic, pulse: view.bp.pulse } })} />
        ) : view.name === 'knows' ? (
          <Knows seniorId={seniorId} onBack={() => setView({ name: 'home' })} toast={toast} />
        ) : today ? (
          <Home
            today={today}
            listening={talk.state === 'listening'}
            interim={talk.interim}
            onPills={() => (today.pills_taken ? toast(t('home.pills.done')) : checkin(t('checkin.text.pills'), 'button', 'common.saved'))}
            onBP={() => setView({ name: 'bp' })}
            onFeel={() => setView({ name: 'feel' })}
            onTalkStart={talk.supported ? talk.start : () => setView({ name: 'feel' })}
            onTalkStop={talk.stop}
            onNotForMe={async (id) => {
              try {
                await api.notForMe(seniorId, id);
                setToday({ ...today, suggestions: today.suggestions.filter((s) => s.id !== id) });
                toast(t('suggest.removed'));
              } catch {
                toast(t('common.offline'));
              }
            }}
            onKnows={() => setView({ name: 'knows' })}
          />
        ) : (
          <p className="sa-loading" aria-busy>…</p>
        )}
        <Toast text={toastText} />
      </div>
    </LangContext.Provider>
  );
}
