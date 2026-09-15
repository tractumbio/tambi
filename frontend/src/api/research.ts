export interface ResearchFinding {
  question: string;
  finding: string;
  sources: string[];
}

export interface ResearchReport {
  title: string;
  brief: string;
  executive_summary: string;
  findings: ResearchFinding[];
  recommendation: string;
  sources: string[];
}

export async function commissionResearch(title: string, brief: string): Promise<ResearchReport> {
  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";
  const resp = await fetch(`${API_BASE_URL}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, brief }),
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
  return resp.json() as Promise<ResearchReport>;
}
