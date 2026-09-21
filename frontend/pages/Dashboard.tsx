import { useEffect, useState } from 'react';
import QuestionForm from '../components/QuestionForm';
import { recurringIssues, RecurringIssue, TroubleshootResponse } from '../src/api';

export default function Dashboard() {
  const [result, setResult] = useState<TroubleshootResponse | null>(null);
  const [issues, setIssues] = useState<RecurringIssue[]>([]);

  useEffect(() => {
    recurringIssues().then(setIssues).catch(() => setIssues([]));
  }, []);

  return <main>
    <h1>PlantOps AI</h1>
    <QuestionForm onResult={setResult} />
    {result && <section aria-live="polite"><h2>{result.severity} priority</h2><p>{result.answer}</p><h3>Next checks</h3><ul>{result.next_checks.map((check) => <li key={check}>{check}</li>)}</ul></section>}
    <section><h2>Recurring issues</h2>{issues.length === 0 ? <p>No historical issues recorded.</p> : <ul>{issues.map((issue) => <li key={`${issue.equipment}-${issue.alarm_code}`}>{issue.equipment}: {issue.alarm_code} ({issue.occurrences})</li>)}</ul>}</section>
  </main>;
}
