// Log my BP: copy the numbers off the cuff. The app never shows a verdict on the numbers.
import { useState } from 'react';
import { useT } from '../../shared/i18n';
import { BigButton, Screen } from '../ui';

export interface BPEntry { systolic: number; diastolic: number; pulse: number | null }

export function LogBP({ initial, busy, onSave, onBack }: {
  initial?: Partial<BPEntry>;
  busy: boolean;
  onSave: (bp: BPEntry) => void;
  onBack: () => void;
}) {
  const t = useT();
  const [sys, setSys] = useState(initial?.systolic?.toString() ?? '');
  const [dia, setDia] = useState(initial?.diastolic?.toString() ?? '');
  const [pulse, setPulse] = useState(initial?.pulse?.toString() ?? '');
  const [problem, setProblem] = useState<'missing' | 'check' | null>(null);

  const save = (confirmed = false) => {
    const s = Number(sys), d = Number(dia), p = pulse ? Number(pulse) : null;
    if (!s || !d) return setProblem('missing');
    const plausible = s > d && s >= 60 && s <= 280 && d >= 30 && d <= 160;
    if (!plausible && !confirmed) return setProblem('check');
    onSave({ systolic: s, diastolic: d, pulse: p });
  };

  const field = (id: string, label: string, value: string, set: (v: string) => void) => (
    <div className="sa-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} inputMode="numeric" pattern="[0-9]*" maxLength={3} value={value}
        onChange={(e) => { set(e.target.value.replace(/\D/g, '')); setProblem(null); }} />
    </div>
  );

  return (
    <Screen title={t('bp.title')} onBack={onBack}>
      <p className="sa-note">{t('bp.hint')}</p>
      <div className="sa-bp">
        {field('sa-sys', t('bp.top'), sys, setSys)}
        {field('sa-dia', t('bp.bottom'), dia, setDia)}
        {field('sa-pulse', t('bp.pulse'), pulse, setPulse)}
      </div>

      {problem === 'missing' && <p className="sa-note sa-warn">{t('bp.missing')}</p>}
      {problem === 'check' ? (
        <div className="sa-card sa-warn">
          <p className="sa-card-label">{t('bp.check')}</p>
          <p>{t('bp.checkBody')}</p>
          <div className="sa-row">
            <BigButton tone="primary" label={t('common.yes')} onClick={() => save(true)} disabled={busy} />
            <BigButton label={t('common.no')} onClick={() => setProblem(null)} />
          </div>
        </div>
      ) : (
        <BigButton tone="primary" label={t('common.save')} onClick={() => save()} disabled={busy} />
      )}
    </Screen>
  );
}
