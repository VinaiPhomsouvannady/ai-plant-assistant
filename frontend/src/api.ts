export type Severity = 'low' | 'medium' | 'high';

export interface Source {
  id: string;
  title: string;
  equipment: string;
  excerpt: string;
  score: number;
}

export interface TroubleshootResponse {
  answer: string;
  severity: Severity;
  next_checks: string[];
  sources: Source[];
  generated_by: string;
}

export interface RecurringIssue {
  equipment: string;
  alarm_code: string;
  occurrences: number;
  first_seen: string;
  last_seen: string;
  latest_message: string;
}

export interface DocumentRecord {
  id: string;
  title: string;
  equipment: string;
  content: string;
  source: string | null;
  chunks: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function troubleshoot(equipment: string, problem: string): Promise<TroubleshootResponse> {
  return request<TroubleshootResponse>('/api/troubleshoot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ equipment, problem }),
  });
}

export function recurringIssues(): Promise<RecurringIssue[]> {
  return request<RecurringIssue[]>('/api/alarms/recurring');
}

export function listDocuments(): Promise<DocumentRecord[]> {
  return request<DocumentRecord[]>('/api/documents');
}

export function searchDocuments(query: string, equipment?: string, limit = 3): Promise<Source[]> {
  return request<Source[]>('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, equipment, limit }),
  });
}
