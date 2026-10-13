// A number heard with low confidence is read back for the senior to confirm. Never guessed.
import { useT } from '../../shared/i18n';
import type { BP } from '../types';
import { BigButton, Screen } from '../ui';

export function Confirm({ bp, busy, onYes, onNo }: { bp: BP; busy: boolean; onYes: () => void; onNo: () => void }) {
  const t = useT();
  return (
    <Screen title={t('confirm.title')}>
      {bp.span && <p className="sa-heard">{t('checkin.heard')} “{bp.span}”</p>}
      <p className="sa-readback">
        {t('confirm.bp', { sys: bp.systolic, dia: bp.diastolic })}
        {bp.pulse != null && <><br />{t('confirm.pulse', { pulse: bp.pulse })}</>}
      </p>
      <div className="sa-buttons">
        <BigButton tone="primary" label={t('confirm.yes')} onClick={onYes} disabled={busy} />
        <BigButton label={t('confirm.no')} onClick={onNo} disabled={busy} />
      </div>
    </Screen>
  );
}
