// Rung R: full screen, one big call button. The words come from write() and its guardrail.
import { useT } from '../../shared/i18n';
import type { Message } from '../types';
import { BigButton, Icon } from '../ui';

export function RedFlag({ message, onClose }: { message: Message; onClose: () => void }) {
  const t = useT();
  return (
    <section className="sa-redflag" role="alertdialog" aria-labelledby="sa-rf-title" aria-describedby="sa-rf-text">
      <h1 id="sa-rf-title">{t('redflag.title')}</h1>
      <p id="sa-rf-text" className="sa-rf-text">{message.text}</p>
      <a className="sa-big sa-call" href="tel:995">
        <span className="sa-big-icon" aria-hidden>{Icon.phone}</span>
        <span>{t('redflag.call')}</span>
      </a>
      <BigButton label={t('common.back')} onClick={onClose} />
    </section>
  );
}
