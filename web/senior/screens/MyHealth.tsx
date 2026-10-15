// "My medicines and check-ups": what each of my medicines is for, in my language, and which vaccines and
// check-ups are due. The words come from the API's fixed notes (backend/reports/medicines.py, prevention.py),
// not a model. A medicine CareLoop doesn't know says so and points to the pharmacist.
import { useEffect, useState } from 'react';
import type { MedicinesView, PreventionView } from '../../shared/contract';
import { useT, type Lang } from '../../shared/i18n';
import { api } from '../api';
import { Icon, Screen } from '../ui';

export function MyHealth({ seniorId, lang, onBack, toast }: { seniorId: string; lang: Lang; onBack: () => void; toast: (s: string) => void }) {
  const t = useT();
  const [meds, setMeds] = useState<MedicinesView | null>(null);
  const [checks, setChecks] = useState<PreventionView | null>(null);

  useEffect(() => {
    api.medicines(seniorId, lang).then(setMeds).catch(() => toast(t('common.offline')));
    api.prevention(seniorId, lang).then(setChecks).catch(() => setChecks(null));
  }, [seniorId, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const open = checks?.items.filter((i) => i.status === 'due' || i.status === 'not_recorded') ?? [];

  return (
    <Screen title={t('meds.title')} onBack={onBack}>
      <section className="sa-card sa-meds">
        <p className="sa-card-label"><span aria-hidden>{Icon.pill}</span> {t('meds.medicines')}</p>
        {meds && meds.medicines.length === 0 && <p>{t('meds.empty')}</p>}
        {meds?.medicines.map((m) => (
          <article key={m.name} className="sa-med">
            <h2>{m.name.charAt(0).toUpperCase() + m.name.slice(1)}</h2>
            <p className={m.known ? 'sa-med-for' : 'sa-med-for is-unknown'}>{m.what_for}</p>
            <p className="sa-note">
              {t('meds.howTake')}: {m.dose_text}
              {m.when.length ? `, ${m.when.join(', ')}` : ''}
            </p>
            {m.known && (
              <details className="sa-med-more">
                <summary>{t('meds.more')}</summary>
                {m.how_it_helps && <p>{m.how_it_helps}</p>}
                <ul>
                  {m.look_out_for.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        ))}
        {meds && meds.medicines.length > 0 && <p className="sa-note">{meds.always}</p>}
      </section>

      {checks && (
        <section className="sa-card sa-checks">
          <p className="sa-card-label">{t('meds.checkups')}</p>
          {open.length === 0 ? (
            <p>{t('meds.allDone')}</p>
          ) : (
            <ul className="sa-check-list">
              {open.map((i) => (
                <li key={i.id}>
                  <p>
                    <strong>{i.title}</strong> <span className={`sa-tag sa-status is-${i.status}`}>{i.status_text}</span>
                  </p>
                  <p className="sa-note">{i.why}</p>
                  <p className="sa-note">{t('meds.where')}: {i.where}</p>
                </li>
              ))}
            </ul>
          )}
          <p className="sa-note">{t('meds.tellFamily')}</p>
        </section>
      )}
    </Screen>
  );
}
