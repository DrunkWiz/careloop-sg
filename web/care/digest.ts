// The weekly digest in words: at most 5 lines from GET /care/family's digest numbers.
// Fixed templates, no model: every line restates a number the API already gave. The numbers only
// include readings when the senior chose to share them (the API leaves them null otherwise).
import type { Digest } from '../shared/contract';

const days = (n: number) => `${n} day${n === 1 ? '' : 's'}`;

export function digestLines(d: Digest, name: string): string[] {
  const lines: string[] = [];

  lines.push(
    d.headline === 'quiet'
      ? `A quiet week for ${name}.`
      : d.headline === 'worth a look'
        ? `A mostly steady week for ${name}, with one thing noted below.`
        : `This week needs you. See the handover above.`,
  );

  lines.push(
    `Checked in on ${d.checkin_days} of 7 days. Pills taken on ${days(d.pills_taken_days)}` +
      (d.missed_days ? `, missed on ${days(d.missed_days)}.` : '.'),
  );

  if (d.mean_systolic != null && d.mean_diastolic != null && d.baseline) {
    const diff = Math.round(d.mean_systolic - d.baseline.systolic);
    lines.push(
      `Blood pressure averaged ${Math.round(d.mean_systolic)}/${Math.round(d.mean_diastolic)} over ${days(d.readings_days)}, ` +
        `against their usual ${Math.round(d.baseline.systolic)}/${Math.round(d.baseline.diastolic)}` +
        (Math.abs(diff) >= 5 ? ` (${diff > 0 ? '+' : ''}${diff}).` : '.'),
    );
  } else {
    lines.push(`Blood pressure logged on ${d.readings_days} of 7 days.`);
  }

  if (d.social_days) lines.push(`Saw or spoke to someone on ${days(d.social_days)}.`);

  const raise = d.worth_raising[d.worth_raising.length - 1];
  lines.push(raise ? `Worth raising at the next visit: ${raise}.` : 'Nothing to raise at the next visit.');

  return lines.slice(0, 5);
}
