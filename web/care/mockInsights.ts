// Offline mocks for /insights and /activities: real API output from the demo (seed, then +11 days),
// recorded into fixtures/insights-demo.json. Regenerate it the same way if the shapes change.
// The two mock-only AAC seniors borrow a demo senior's data: Mr Ong gets Mr Tan's rising BP, Mdm Aminah Mr Ng's quiet week.
import type { Activities, Insights } from '../shared/contract';
import fixtures from './fixtures/insights-demo.json';
import { delay } from './mock';

const SOURCE: Record<string, string> = { tan: 'tan', lee: 'lee', goh: 'goh', ng: 'ng', ong: 'tan', aminah: 'ng' };
const data = fixtures as unknown as { insights: Record<string, Insights>; activities: Record<string, Activities> };

export function getInsights(seniorId: string): Promise<Insights> {
  return delay(data.insights[SOURCE[seniorId] ?? 'lee']);
}

export function getActivities(seniorId: string): Promise<Activities> {
  return delay(data.activities[SOURCE[seniorId] ?? 'lee']);
}
