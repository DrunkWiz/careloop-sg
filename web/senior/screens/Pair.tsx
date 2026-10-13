// Pairing: a family member (or the AAC worker if there is no family) sets the app up with a
// code from the caregiver app, and chooses with the senior what is shared.
import { useState } from 'react';
import { useT, type Lang } from '../../shared/i18n';
import { api } from '../api';
import type { Consent, PairResult } from '../types';
import { BigButton, Screen } from '../ui';

const LANGS: { lang: Lang; label: string }[] = [
  { lang: 'en', label: 'English' },
  { lang: 'en-SG', label: 'Singlish' },
  { lang: 'zh', label: '中文' },
];

export function Pair({ lang, setLang, onPaired }: { lang: Lang; setLang: (l: Lang) => void; onPaired: (r: PairResult) => void }) {
  const t = useT();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState(false);
  const [consent, setConsent] = useState<Consent>({ share_bp: true, share_meds: true, share_words: false, share_activity: true });

  const submit = async () => {
    setBusy(true);
    setBad(false);
    try {
      onPaired(await api.pair(code, lang, consent));
    } catch {
      setBad(true);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (key: keyof Consent, label: string) => (
    <label className="sa-toggle">
      <input type="checkbox" checked={consent[key]} onChange={(e) => setConsent({ ...consent, [key]: e.target.checked })} />
      <span>{label}</span>
    </label>
  );

  return (
    <Screen title={t('pair.title')}>
      <p className="sa-note">{t('pair.intro')}</p>

      <fieldset className="sa-fieldset">
        <legend>{t('pair.language')}</legend>
        <div className="sa-row">
          {LANGS.map((l) => (
            <button key={l.lang} className={`sa-chip${lang === l.lang ? ' sa-on' : ''}`} aria-pressed={lang === l.lang} onClick={() => setLang(l.lang)}>
              {l.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="sa-field">
        <label htmlFor="sa-code">{t('pair.code')}</label>
        <input id="sa-code" inputMode="numeric" pattern="[0-9]*" maxLength={6} placeholder={t('pair.codePlaceholder')}
          value={code} onChange={(e) => { setCode(e.target.value.replace(/\D/g, '')); setBad(false); }} />
      </div>

      <fieldset className="sa-fieldset">
        <legend>{t('pair.consent')}</legend>
        {toggle('share_bp', t('pair.consent.bp'))}
        {toggle('share_meds', t('pair.consent.meds'))}
        {toggle('share_words', t('pair.consent.words'))}
        {toggle('share_activity', t('pair.consent.activity'))}
        <p className="sa-note">{t('pair.consent.note')}</p>
      </fieldset>

      {bad && <p className="sa-note sa-warn">{t('pair.badCode')}</p>}
      <BigButton tone="primary" label={t('pair.submit')} onClick={submit} disabled={busy || code.length !== 6} />
    </Screen>
  );
}
