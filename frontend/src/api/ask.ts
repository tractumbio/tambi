export interface AskResponse {
  question: string;
  answer: string;
  sql: string;
  sources: string[];
  row_count: number;
  columns: string[];
  rows: Record<string, unknown>[];
}

export async function askMarket(question: string): Promise<AskResponse> {
  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";
  const resp = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<AskResponse>;
}
