// "How I feel": talk, type, or tap a quick answer. Everything goes to POST /checkin as text.
import { useState } from 'react';
import { useT } from '../../shared/i18n';
import { BigButton, Screen, TalkButton } from '../ui';
import type { TalkState } from '../useHoldToTalk';

export function Feel({ prompt, talk, busy, onSend, onBack }: {
  prompt: string;
  talk: { state: TalkState; interim: string; start: () => void; stop: () => void; supported: boolean };
  busy: boolean;
  onSend: (text: string, source: 'typed' | 'button') => void;
  onBack: () => void;
}) {
  const t = useT();
  const [text, setText] = useState('');
  const listening = talk.state === 'listening';

  return (
    <Screen title={t('home.feel')} onBack={onBack}>
      <p className="sa-prompt">{prompt}</p>

      {talk.supported ? (
        <>
          <TalkButton listening={listening} disabled={busy} onStart={talk.start} onStop={talk.stop}
            label={listening ? t('checkin.release') : t('checkin.hold')} />
          {listening && <p className="sa-interim" aria-live="polite">{talk.interim || t('checkin.listening')}</p>}
          {talk.state === 'denied' && <p className="sa-note">{t('checkin.micDenied')}</p>}
        </>
      ) : (
        <p className="sa-note">{t('checkin.noSpeech')}</p>
      )}

      <div className="sa-quick">
        <BigButton label={t('checkin.quick.good')} onClick={() => onSend(t('checkin.text.good'), 'button')} disabled={busy} />
        <BigButton label={t('checkin.quick.ok')} onClick={() => onSend(t('checkin.text.ok'), 'button')} disabled={busy} />
        <BigButton label={t('checkin.quick.unwell')} onClick={() => onSend(t('checkin.text.unwell'), 'button')} disabled={busy} />
      </div>

      <form className="sa-typed" onSubmit={(e) => { e.preventDefault(); if (!busy && text.trim()) onSend(text.trim(), 'typed'); }}>
        <label htmlFor="sa-feel-text">{t('checkin.type')}</label>
        <textarea id="sa-feel-text" rows={3} value={text} placeholder={t('checkin.placeholder')} onChange={(e) => setText(e.target.value)} />
        <BigButton tone="primary" label={t('common.send')} onClick={() => text.trim() && onSend(text.trim(), 'typed')} disabled={busy || !text.trim()} />
      </form>
    </Screen>
  );
}
