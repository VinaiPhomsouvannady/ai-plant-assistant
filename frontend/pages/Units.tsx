import { useEffect, useMemo, useState } from 'react';
import { AlarmRecord, DocumentRecord, listAlarms, listDocuments } from '../src/api';

interface UnitsProps {
  onLogout?: () => void;
}

export default function Units({ onLogout }: UnitsProps) {
  const [alarms, setAlarms] = useState<AlarmRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);

  useEffect(() => {
    Promise.all([listAlarms(), listDocuments()]).then(([nextAlarms, nextDocuments]) => {
      setAlarms(nextAlarms);
      setDocuments(nextDocuments);
    }).catch(() => { setAlarms([]); setDocuments([]); });
  }, []);

  const units = useMemo(() => {
    const names = new Set([...alarms.map((alarm) => alarm.equipment), ...documents.map((document) => document.equipment)]);
    return [...names].sort().map((name) => ({
      name,
      alarms: alarms.filter((alarm) => alarm.equipment === name),
      documents: documents.filter((document) => document.equipment === name),
    }));
  }, [alarms, documents]);

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand-lockup"><span className="brand-mark">+</span><div><p className="eyebrow">Plant Operations Console</p><h1>Units</h1></div></div>
        <div className="topbar-actions"><a href="/" className="nav-link">Dashboard</a><a href="/alarms" className="nav-link">Alarms</a><a href="/documents" className="nav-link">Documents</a>{onLogout && <button type="button" className="nav-link" onClick={onLogout}>Sign out</button>}</div>
      </header>
      <section className="page-heading"><div><p className="eyebrow">Equipment overview</p><h2>Plant units</h2></div><span className="status-pill">{units.length} tracked</span></section>
      <section className="unit-grid">
        {units.map((unit) => <article className="unit-card" key={unit.name}><div className="unit-card-header"><div><span className="unit-status" /> <strong>{unit.name}</strong></div><span className={unit.alarms.length ? 'alarm-count active' : 'alarm-count'}>{unit.alarms.length} alarms</span></div><div className="unit-metrics"><span><b>{unit.documents.length}</b> documents</span><span><b>{unit.alarms.length ? unit.alarms[0].alarm_code : 'Clear'}</b> latest status</span></div>{unit.alarms[0] && <p className="unit-message">{unit.alarms[0].message}</p>}</article>)}
        {!units.length && <p className="empty-state">No units are available yet. Add a document or alarm to begin tracking equipment.</p>}
      </section>
    </main>
  );
}