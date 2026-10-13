// "What CareLoop knows about me": plain-language list, every item erasable.
import { useEffect, useState } from 'react';
import { useT } from '../../shared/i18n';
import { api } from '../api';
import type { KnownFact } from '../types';
import { Screen } from '../ui';

export function Knows({ seniorId, onBack, toast }: { seniorId: string; onBack: () => void; toast: (s: string) => void }) {
  const t = useT();
  const [facts, setFacts] = useState<KnownFact[] | null>(null);

  useEffect(() => {
    api.knows(seniorId).then(setFacts).catch(() => toast(t('common.offline')));
  }, [seniorId]); // eslint-disable-line react-hooks/exhaustive-deps

  const erase = async (id: string) => {
    try {
      await api.forget(seniorId, id);
      setFacts((f) => f?.filter((x) => x.id !== id) ?? null);
      toast(t('knows.erased'));
    } catch {
      toast(t('common.offline'));
    }
  };

  return (
    <Screen title={t('knows.title')} onBack={onBack}>
      <p className="sa-note">{t('knows.intro')}</p>
      {facts?.length === 0 && <p>{t('knows.empty')}</p>}
      <ul className="sa-knows">
        {facts?.map((f) => (
          <li key={f.id}>
            <span>{f.text}</span>
            <button className="sa-erase" onClick={() => erase(f.id)}>{t('knows.erase')}</button>
          </li>
        ))}
      </ul>
    </Screen>
  );
}
