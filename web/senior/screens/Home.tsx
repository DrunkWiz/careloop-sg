// Home: the three daily buttons, the hold-to-talk mic, the morning check-in, haze line and suggestions.
import { useContext } from 'react';
import { LangContext, useT } from '../../shared/i18n';
import type { Today } from '../types';
import { BigButton, Icon, TalkButton } from '../ui';

export function Home({ today, listening, interim, onPills, onBP, onFeel, onTalkStart, onTalkStop, onNotForMe, onKnows }: {
  today: Today;
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

  return (
    <div className="sa-home">
      <h1 className="sa-greeting">{greeting}{today.senior.name ? comma + today.senior.name : ''}</h1>

      {today.checkin_due && (
        <div className="sa-card sa-checkin">
          <p className="sa-card-label">{t('checkin.title')}</p>
          {/* The engine's question, never a number. */}
          <p className="sa-prompt">{today.prompt?.text || t('checkin.default')}</p>
        </div>
      )}

      <div className="sa-buttons">
        <BigButton icon={Icon.pill} label={t(today.pills_taken ? 'home.pills.done' : 'home.pills')} done={today.pills_taken} onClick={onPills} />
        <BigButton icon={Icon.heart} label={t(today.bp_logged ? 'home.bp.done' : 'home.bp')} done={today.bp_logged} onClick={onBP} />
        <BigButton icon={Icon.smile} label={t('home.feel')} done={today.feel_logged} onClick={onFeel} />
      </div>

      <TalkButton listening={listening} onStart={onTalkStart} onStop={onTalkStop}
        label={listening ? t('checkin.release') : t('home.talk')} />
      {listening && <p className="sa-interim" aria-live="polite">{interim || t('checkin.listening')}</p>}

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
    </div>
  );
}
