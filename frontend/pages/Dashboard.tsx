import { useEffect, useState } from 'react';
import QuestionForm from '../components/QuestionForm';
import {
  createDocument,
  DocumentRecord,
  listDocuments,
  recurringIssues,
  RecurringIssue,
  searchDocuments,
  Source,
  TroubleshootResponse,
  uploadDocument,
} from '../src/api';

interface DashboardProps {
  token?: string;
  onLogout?: () => void;
}

const severityStyles: Record<string, string> = {
  low: 'severity-low',
  medium: 'severity-medium',
  high: 'severity-high',
};

const statusCards = [
  { label: 'Units online', value: '23 / 26', tone: 'good' },
  { label: 'Active alarms', value: '4', tone: 'warn' },
  { label: 'Avg response', value: '12 min', tone: 'neutral' },
];

export default function Dashboard({ token = '', onLogout }: DashboardProps) {
  const [result, setResult] = useState<TroubleshootResponse | null>(null);
  const [issues, setIssues] = useState<RecurringIssue[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('low discharge pressure');
  const [searchResults, setSearchResults] = useState<Source[]>([]);
  const [documentTitle, setDocumentTitle] = useState('Pump startup checklist');
  const [documentEquipment, setDocumentEquipment] = useState('Centrifugal pump');
  const [documentSource, setDocumentSource] = useState('Operations manual');
  const [documentContent, setDocumentContent] = useState(
    'Check suction pressure, verify discharge flow, and inspect the strainer before escalating the issue.'
  );
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState('');
  const [documentLoading, setDocumentLoading] = useState(false);

  useEffect(() => {
    recurringIssues().then(setIssues).catch(() => setIssues([]));
    listDocuments().then(setDocuments).catch(() => setDocuments([]));
  }, []);

  async function refreshDocuments() {
    try {
      const nextDocuments = await listDocuments();
      setDocuments(nextDocuments);
    } catch {
      setDocuments([]);
    }
  }

  async function handleKnowledgeSearch() {
    if (!searchQuery.trim()) {
      return;
    }

    try {
      const results = await searchDocuments(searchQuery, documentEquipment || undefined, 3);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
  }

  async function handleDocumentSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDocumentLoading(true);
    setDocumentError('');

    try {
      if (uploadFile) {
        await uploadDocument(
          uploadFile,
          documentTitle.trim() || uploadFile.name.replace(/\.[^.]+$/, ''),
          documentEquipment.trim(),
          documentSource.trim() || undefined,
          token,
        );
      } else if (!documentTitle.trim() || !documentEquipment.trim() || !documentContent.trim()) {
        setDocumentError('Please complete the title, equipment, and procedure content or choose a file to upload.');
        return;
      } else {
        await createDocument({
          title: documentTitle.trim(),
          equipment: documentEquipment.trim(),
          content: documentContent.trim(),
          source: documentSource.trim() || null,
        }, token);
      }

      setDocumentTitle('');
      setDocumentSource('');
      setDocumentContent('');
      setUploadFile(null);
      await refreshDocuments();
    } catch (error) {
      setDocumentError(error instanceof Error ? error.message : 'Unable to save this document.');
    } finally {
      setDocumentLoading(false);
    }
  }

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">+</span>
          <div>
            <p className="eyebrow">Plant Operations Console</p>
            <h1>
              PlantOps <b>AI</b>
            </h1>
          </div>
        </div>
        <div className="topbar-actions">
          <a href="/units" className="nav-link">Units</a>
          <a href="/alarms" className="nav-link">Alarms</a>
          <a href="/documents" className="nav-link">Documents</a>
          <div className="status-pill">Live monitoring</div>
          {onLogout && <button type="button" className="nav-link" onClick={onLogout}>Sign out</button>}
        </div>
      </header>

      <section className="status-row">
        {statusCards.map((card) => (
          <div key={card.label} className={`status-card ${card.tone}`}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </div>
        ))}
      </section>

      <section className="hero-grid">
        <div className="panel panel-primary">
          <div className="panel-header">
            <span className="dot" />
            <h2>Equipment triage</h2>
          </div>
          <QuestionForm onResult={setResult} />
        </div>

        <aside className="panel panel-secondary">
          <h3>Recurring issues</h3>
          {issues.length === 0 ? (
            <p className="empty-state">No historical issues recorded yet.</p>
          ) : (
            <ul className="issue-list">
              {issues.map((issue) => (
                <li key={`${issue.equipment}-${issue.alarm_code}`}>
                  <div className="issue-title-row">
                    <strong>{issue.equipment}</strong>
                    <span>{issue.occurrences}x</span>
                  </div>
                  <p>{issue.alarm_code}</p>
                  <small>{issue.latest_message}</small>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </section>

      <section className="insight-grid">
        <div className="panel panel-secondary">
          <h3>Process trend</h3>
          <div className="trend-chart" aria-label="Process trend chart">
            <span className="trend-line" />
          </div>
          <div className="trend-labels">
            <span>10:00</span>
            <span>12:00</span>
            <span>14:00</span>
          </div>
        </div>

        <div className="panel panel-secondary knowledge-panel">
          <h3>Knowledge base</h3>
          <div className="search-row">
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search plant procedure docs"
            />
            <button type="button" onClick={handleKnowledgeSearch}>Search</button>
          </div>

          <div className="knowledge-results">
            {searchResults.length === 0 ? (
              <p className="empty-state">{documents.length ? 'Try a search to find relevant procedures.' : 'No documents loaded yet.'}</p>
            ) : (
              searchResults.map((item) => (
                <div key={item.id} className="knowledge-item">
                  <strong>{item.title}</strong>
                  <p>{item.excerpt}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="panel panel-secondary document-panel">
        <div className="panel-header">
          <span className="dot" />
          <h2>Document handling</h2>
        </div>

        <form className="document-form" onSubmit={handleDocumentSubmit}>
          <div className="field-grid">
            <div className="field-group">
              <label htmlFor="document-title">Procedure title</label>
              <input
                id="document-title"
                value={documentTitle}
                onChange={(event) => setDocumentTitle(event.target.value)}
                placeholder="Pump startup checklist"
              />
            </div>

            <div className="field-group">
              <label htmlFor="document-equipment">Equipment</label>
              <input
                id="document-equipment"
                value={documentEquipment}
                onChange={(event) => setDocumentEquipment(event.target.value)}
                placeholder="Centrifugal pump"
              />
            </div>

            <div className="field-group full-width">
              <label htmlFor="document-source">Source</label>
              <input
                id="document-source"
                value={documentSource}
                onChange={(event) => setDocumentSource(event.target.value)}
                placeholder="Operations manual / SOP / vendor bulletin"
              />
            </div>

            <div className="field-group full-width">
              <label htmlFor="document-content">Procedure content</label>
              <textarea
                id="document-content"
                value={documentContent}
                onChange={(event) => setDocumentContent(event.target.value)}
                rows={6}
                placeholder="Paste or type the plant procedure steps here..."
              />
            </div>
          </div>

          <div className="upload-row">
            <label className="upload-box">
              <input
                type="file"
                accept=".txt,.md,.pdf"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              />
              <span>{uploadFile ? uploadFile.name : 'Upload procedure file'}</span>
            </label>
          </div>

          <div className="form-actions align-left">
            <button type="submit" disabled={documentLoading}>
              {documentLoading ? 'Saving document...' : 'Add document'}
            </button>
          </div>

          {documentError && <p className="error-banner">{documentError}</p>}
        </form>
      </section>

      {result && (
        <section className="panel result-panel" aria-live="polite">
          <div className="result-header">
            <div>
              <p className="eyebrow">AI recommendation</p>
              <h2>Recommended response</h2>
            </div>
            <span className={`severity-badge ${severityStyles[result.severity] ?? 'severity-low'}`}>
              {result.severity} priority
            </span>
          </div>

          <p className="answer-copy">{result.answer}</p>

          <div className="result-grid">
            <div>
              <h3>Next checks</h3>
              <ul className="check-list">
                {result.next_checks.map((check) => (
                  <li key={check}>{check}</li>
                ))}
              </ul>
            </div>

            <div>
              <h3>Source references</h3>
              <ul className="source-list">
                {result.sources.map((source) => (
                  <li key={source.id}>
                    <strong>{source.title}</strong>
                    <span>score {source.score.toFixed(2)}</span>
                    <p>{source.excerpt}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="meta-row">
            <span>Generated by: {result.generated_by}</span>
          </div>
        </section>
      )}
    </main>
  );
}
