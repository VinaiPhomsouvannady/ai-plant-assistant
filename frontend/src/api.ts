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
  const response = await fetch(path, { ...options, credentials: 'include' });
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

export function createDocument(payload: {
  title: string;
  equipment: string;
  content: string;
  source?: string | null;
}, token = ''): Promise<DocumentRecord> {
  return request<DocumentRecord>('/api/documents', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
}

export function uploadDocument(file: File, title: string, equipment: string, source?: string, token = ''): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  formData.append('equipment', equipment);
  if (source) {
    formData.append('source', source);
  }

  return fetch('/api/documents/upload', {
    method: 'POST',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: formData,
  }).then(async (response) => {
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Upload failed');
    }
    return response.json() as Promise<DocumentRecord>;
  });
}

export function searchDocuments(query: string, equipment?: string, limit = 3): Promise<Source[]> {
  return request<Source[]>('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, equipment, limit }),
  });
}
