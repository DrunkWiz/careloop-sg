// Home: the three daily buttons, the hold-to-talk mic, the morning check-in, haze line and suggestions.
import { useContext } from 'react';
import { LangContext, useT } from '../../shared/i18n';
import type { Today } from '../types';
import { BigButton, Icon, TalkButton } from '../ui';

export function Home({ today, busy, talkSupported, listening, interim, onPills, onBP, onFeel, onTalkStart, onTalkStop, onNotForMe, onKnows }: {
  today: Today;
  busy: boolean;
  talkSupported: boolean;
  listening: boolean;
  interim: string;
  onPills: () => void;
  onBP: () => void;
  onFeel: () => void;
  onTalkStart: () => void;
  onTalkStop: () => void;
  onNotForMe: (id: string) => void;
  onKnows: () => void;
}) {
  const t = useT();
  const comma = useContext(LangContext) === 'zh' ? '，' : ', ';
  const hour = new Date().getHours();
  const greeting = t(hour < 12 ? 'home.greeting.morning' : hour < 18 ? 'home.greeting.afternoon' : 'home.greeting.evening');
  const lang = useContext(LangContext);
  const complete = [today.pills_taken, today.bp_logged, today.feel_logged].filter(Boolean).length;
  const date = new Date(today.date ? `${today.date}T12:00:00` : Date.now()).toLocaleDateString(lang === 'zh' ? 'zh-SG' : 'en-SG', { weekday: 'long', day: 'numeric', month: 'long' });

  return (
    <div className="sa-home">
      <div className="sa-welcome"><p className="sa-date">{date}</p><h1 className="sa-greeting">{greeting}{today.senior.name ? comma + today.senior.name : ''}</h1><p className="sa-welcome-note">{t('home.subtitle')}</p><span className="sa-sun" aria-hidden="true">☀</span></div>
      <div className="sa-home-grid"><section className="sa-daily">
      <div className="sa-daily-head"><h2>{t('home.today')}</h2><span>{t('home.progress', { count: complete })}</span></div>
      <div className="sa-progress" aria-hidden="true">{[0,1,2].map((i) => <span key={i} className={i < complete ? 'is-complete' : ''} />)}</div>

      {today.checkin_due && (
        <div className="sa-card sa-checkin">
          <p className="sa-card-label">{t('checkin.title')}</p>
          {/* The engine's question, never a number. */}
          <p className="sa-prompt">{today.prompt?.text || t('checkin.default')}</p>
        </div>
      )}

      <div className="sa-buttons">
        <BigButton icon={Icon.pill} label={t(today.pills_taken ? 'home.pills.done' : 'home.pills')} done={today.pills_taken} onClick={onPills} disabled={busy} />
        <BigButton icon={Icon.heart} label={t(today.bp_logged ? 'home.bp.done' : 'home.bp')} done={today.bp_logged} onClick={onBP} disabled={busy} />
        <BigButton icon={Icon.smile} label={t('home.feel')} done={today.feel_logged} onClick={onFeel} disabled={busy} />
      </div>

      {talkSupported ? <TalkButton disabled={busy} listening={listening} onStart={onTalkStart} onStop={onTalkStop}
        label={listening ? t('checkin.release') : t('home.talk')} /> : <BigButton tone="primary" icon={Icon.list} label={t('home.type')} onClick={onFeel} disabled={busy} />}
      {talkSupported && <button type="button" className="sa-type-link" onClick={onFeel} disabled={busy}>{t('home.type')}</button>}
      {listening && <p className="sa-interim" aria-live="polite">{interim || t('checkin.listening')}</p>}
      {busy && <p className="sa-note" role="status">{t('common.saving')}</p>}
      </section><aside className="sa-beside">

      {today.haze && (
        <div className="sa-card sa-haze">
          <p className="sa-card-label"><span aria-hidden>{Icon.cloud}</span> {t('haze.title')}</p>
          <p>{today.haze.text}</p>
        </div>
      )}

      {today.suggestions.length > 0 && (
        <div className="sa-card">
          <p className="sa-card-label">{t('suggest.title')}</p>
          <ul className="sa-suggestions">
            {today.suggestions.slice(0, 3).map((s) => (
              <li key={s.id}>
                <div>
                  <p className="sa-place">{s.place}</p>
                  <p className="sa-why">
                    {s.why_it_fits}
                    {s.indoor && <span className="sa-tag">{t('suggest.indoor')}</span>}
                    {s.free && <span className="sa-tag">{t('suggest.free')}</span>}
                  </p>
                </div>
                <button className="sa-notforme" onClick={() => onNotForMe(s.id)}>{t('suggest.notForMe')}</button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button className="sa-link" onClick={onKnows}><span aria-hidden>{Icon.list}</span> {t('home.knows')}</button>
      </aside></div>
    </div>
  );
}
