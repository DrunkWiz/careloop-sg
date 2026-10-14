// "How this was decided": the rule that fired, and who wrote the words. Rules pick the rung; a model may
// only word a message, and every message passes the guardrail or is replaced by a fixed template.
import type { LogDay, Message } from '../shared/contract';
import { TONE_LABEL, toneOf } from './plain';

interface Props {
  ruleId?: string | null;
  day?: LogDay | null;
  message?: Message | null;
}

export default function DecisionInfo({ ruleId, day, message }: Props) {
  const rule = ruleId ?? day?.rule_id ?? null;
  return (
    <details className="care-card decision-info">
      <summary>How this was decided</summary>
      <dl>
        <dt>Who decided</dt>
        <dd>
          CareLoop's fixed rules{rule ? <> (rule <code>{rule}</code>)</> : null}. No AI model chooses who is told, or when.
        </dd>
        {day?.rung != null && (
          <>
            <dt>Level</dt>
            <dd>{TONE_LABEL[toneOf(day.rung)]}</dd>
          </>
        )}
        {message && (
          <>
            <dt>Who wrote the words</dt>
            <dd>
              {message.from_template ? 'A fixed, pre-checked template.' : `Drafted by ${message.model ?? 'a language model'}.`}{' '}
              Safety check: {message.guardrail.passed ? 'passed' : `failed (${message.guardrail.reasons.join(', ')}), so the template was sent`}.
            </dd>
          </>
        )}
        <dt>Thresholds</dt>
        <dd>Starting values, marked as placeholders until a clinician signs them off.</dd>
        <dt>What CareLoop never does</dt>
        <dd>
          Diagnose, or advise on medicines. It only tells the people linked at setup: red flags at once, anything else
          only through a handover that a person then chooses to act on.
        </dd>
      </dl>
    </details>
  );
}
