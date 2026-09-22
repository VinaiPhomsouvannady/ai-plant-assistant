import { useEffect, useMemo, useState } from 'react';
import { AlarmRecord, listAlarms } from '../src/api';

interface AlarmsProps {
  onLogout?: () => void;
}

export default function Alarms({ onLogout }: AlarmsProps) {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    listAlarms().then(setAlarms).catch(() => setAlarms([]));
  }, []);

  const filtered = useMemo(() => alarms.filter((alarm) =>
    `${alarm.equipment} ${alarm.alarm_code} ${alarm.message}`.toLowerCase().includes(filter.toLowerCase())
  ), [alarms, filter]);

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand-lockup"><span className="brand-mark">+</span><div><p className="eyebrow">Plant Operations Console</p><h1>Alarms</h1></div></div>
        <div className="topbar-actions"><a href="/" className="nav-link">Dashboard</a><a href="/units" className="nav-link">Units</a><a href="/documents" className="nav-link">Documents</a>{onLogout && <button type="button" className="nav-link" onClick={onLogout}>Sign out</button>}</div>
      </header>
      <section className="page-heading"><div><p className="eyebrow">Live event stream</p><h2>Alarm history</h2></div><input className="compact-input" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter alarms" /></section>
      <section className="table-panel">
        <div className="table-wrap"><table><thead><tr><th>Equipment</th><th>Alarm</th><th>Message</th><th>Value</th><th>Occurred</th></tr></thead><tbody>
          {filtered.map((alarm) => <tr key={alarm.id}><td><strong>{alarm.equipment}</strong></td><td><span className="alarm-code">{alarm.alarm_code}</span></td><td>{alarm.message}</td><td>{alarm.value ?? '-'} {alarm.unit ?? ''}</td><td>{new Date(alarm.occurred_at).toLocaleString()}</td></tr>)}
          {!filtered.length && <tr><td colSpan={5} className="empty-state">No alarms match this filter.</td></tr>}
        </tbody></table></div>
      </section>
    </main>
  );
}