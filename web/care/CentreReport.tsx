// Centre report: the week for the whole caseload, for the centre manager and for the reports a centre sends
// its funder. Worked out in the browser from the same caseload, decision logs and insights the console loads.
// Two exports, both CSV: every senior's 7-day befriending record, and the summary table.
import type { Caseload } from '../shared/contract';
import type { SeniorExtras } from './AacApp';
import { cap, ruleText } from './plain';

const fmt = (d: string) => new Date(d).toLocaleDateString('en-SG', { day: 'numeric', month: 'short', year: 'numeric' });

function csv(rows: (string | number | null | undefined)[][]): string {
  return rows
    .map((r) => r.map((v) => {
      const s = v == null ? '' : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(','))
    .join('\n');
}

function download(name: string, text: string) {
  // A BOM so Excel opens Chinese check-in words correctly.
  const url = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export default function CentreReport({ data, extras, centre }: { data: Caseload; extras: Record<string, SeniorExtras>; centre: string }) {
  const rows = data.seniors.map((r) => {
    const log = extras[r.senior.id]?.log ?? [];
    const ins = extras[r.senior.id]?.insights;
    return {
      r,
      log,
      replied: log.filter((d) => d.replied).length,
      days: log.length,
      nudges: log.filter((d) => d.rung === '1' || d.rung === '2').length,
      noted: log.filter((d) => d.rung === '3').length,
      handed: log.filter((d) => d.rung === '4').length,
      red: log.filter((d) => d.rung === 'R').length,
      social: log.filter((d) => d.social).length,
      watch: ins?.findings.filter((f) => f.tone === 'watch').map((f) => f.title) ?? [],
      pills: ins ? `${ins.adherence.taken_days}/${ins.adherence.reported_days}` : '',
    };
  });
  const all = rows.flatMap((x) => x.log);
  const replyRate = all.length ? Math.round((all.filter((d) => d.replied).length / all.length) * 100) : null;
  const quietDays = all.filter((d) => d.rung === '0').length;
  const alerts = rows.reduce((n, x) => n + x.handed + x.red, 0);
  const from = all.length ? all.reduce((m, d) => (d.date < m ? d.date : m), all[0].date) : data.today;

  const exportRecords = () =>
    download(
      `befriending-records-${data.today}.csv`,
      csv([
        ['Senior', 'Date', 'Replied', 'Their words', 'Pills', 'Saw people', 'CareLoop decided', 'Rule', 'Reason'],
        ...rows.flatMap(({ r, log }) =>
          [...log].sort((a, b) => a.date.localeCompare(b.date)).map((d) => [
            r.senior.name, d.date, d.replied ? 'yes' : 'no', d.checkins.map((c) => c.raw_text).join(' / '), d.pills ?? '',
            d.social ? 'yes' : '', ruleText(d.rule_id, d.rung), d.rule_id, d.reason ? cap(d.reason) : '',
          ]),
        ),
      ]),
    );

  const exportSummary = () =>
    download(
      `centre-summary-${data.today}.csv`,
      csv([
        ['Senior', 'Check-ins answered', 'Days', 'Gentle nudges', 'Noted', 'Handed over', 'Red flags', 'Social days', 'Pills taken / reported (30 days)', 'Worth watching'],
        ...rows.map((x) => [x.r.senior.name, x.replied, x.days, x.nudges, x.noted, x.handed, x.red, x.social, x.pills, x.watch.join('; ')]),
      ]),
    );

  return (
    <>
      <div className="console-title">
        <h1>Centre report</h1>
        <p className="care-muted">
          {centre} · {fmt(from)} to {fmt(data.today)} · written from CareLoop's decision log, so nothing is typed in twice
        </p>
      </div>

      <div className="tiles">
        <div className="tile"><span className="tile-value">{data.seniors.length}</span><span className="tile-label">Seniors on the caseload</span></div>
        <div className="tile"><span className="tile-value">{replyRate != null ? `${replyRate}%` : '–'}</span><span className="tile-label">Check-ins answered</span><span className="tile-hint">last 7 days</span></div>
        <div className="tile"><span className="tile-value">{quietDays}</span><span className="tile-label">Quiet days logged</span><span className="tile-hint">each with a reason</span></div>
        <div className={`tile ${alerts ? 'is-action' : ''}`}><span className="tile-value">{alerts}</span><span className="tile-label">Handovers and red flags</span><span className="tile-hint">needed a person</span></div>
      </div>

      <div className="report-actions">
        <button className="care-primary" onClick={exportRecords}>Export befriending records (CSV)</button>
        <button className="care-secondary" onClick={exportSummary}>Export this summary (CSV)</button>
      </div>

      <div className="table-scroll">
        <table className="report-table">
          <thead>
            <tr>
              <th>Senior</th>
              <th>Answered</th>
              <th>Nudges</th>
              <th>Noted</th>
              <th>Handed over</th>
              <th>Red flags</th>
              <th>Social days</th>
              <th>Pills (30 d)</th>
              <th>Worth watching</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.r.senior.id}>
                <td>{x.r.senior.name}</td>
                <td className="num">{x.replied}/{x.days}</td>
                <td className="num">{x.nudges}</td>
                <td className="num">{x.noted}</td>
                <td className="num">{x.handed}</td>
                <td className="num">{x.red}</td>
                <td className="num">{x.social}</td>
                <td className="num">{x.pills}</td>
                <td>{x.watch.join('; ') || '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="care-muted">Synthetic people in the demo. Counts cover the last 7 days unless marked.</p>
    </>
  );
}
