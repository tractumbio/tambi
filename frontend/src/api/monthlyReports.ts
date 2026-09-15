const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";

export interface MonthlyReportSummary {
  id: number;
  period_start: string;
  period_end: string;
  generated_at: string;
  status: string;
  model: string | null;
  effort: string | null;
  title: string | null;
  contract_source_count: number;
  news_source_count: number;
}

export interface MonthlyReportOut extends MonthlyReportSummary {
  executive_summary: string | null;
  payload: ReportPayload;
}

export interface NewsItem {
  headline: string | null;
  summary: string | null;
  url: string;
  category: string;
  relevance: string | null;
  entities: string[];
  published_date: string | null;
  is_new: boolean;
}

export interface KnowledgeChange {
  new_items: number;
  prev_window_items: number;
  delta_pct: number | null;
  total_corpus: number;
  by_category: Record<string, number>;
  top_entities: { slug: string; count: number }[];
}

export interface MovementItem {
  cn_id: string | null;
  title: string | null;
  value: number | null;
  agency: string | null;
  supplier: string | null;
  competitor_slug: string | null;
  competitor_label: string;
  date_published: string | null;
  period_end: string | null;
}

export interface MovementSection {
  total_value: number;
  total_count: number;
  by_competitor: { slug: string; label: string; category: string; value: number; count: number }[];
  notable: MovementItem[];
}

export interface ReportPayload {
  structure: string;
  narrative: {
    executive_summary: string;
    contract_movements: string;
    expenditure_trends: string;
    market_news: string;
    implications: string;
  };
  facts: {
    window: { start: string; end: string; label: string; days: number };
    spend: {
      new_award_value: number;
      new_award_count: number;
      prev_window_value: number;
      delta_pct: number | null;
      accenture_value: number;
      accenture_share: number;
    };
    new_awards: MovementSection;
    amendments: MovementSection;
    expiries: MovementSection;
    competitor_momentum: { slug: string; label: string; category: string; value_12m: number; trend: string }[];
    by_theme: { slug: string; label: string; value: number; count: number }[];
    contract_source_cn_ids: string[];
  };
  news: NewsItem[];
  knowledge_change: KnowledgeChange;
  params: { model: string; effort: string };
}

async function j<T>(resp: Response): Promise<T> {
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
  return resp.json() as Promise<T>;
}

export function listReports(): Promise<MonthlyReportSummary[]> {
  return fetch(`${API_BASE_URL}/monthly-reports`).then((r) => j(r));
}

export function getReport(id: number): Promise<MonthlyReportOut> {
  return fetch(`${API_BASE_URL}/monthly-reports/${id}`).then((r) => j(r));
}

export function getDefaultStructure(): Promise<{ structure: string }> {
  return fetch(`${API_BASE_URL}/monthly-reports/default-structure`).then((r) => j(r));
}

export interface GenerateParams {
  month?: string;
  period_start?: string;
  period_end?: string;
  model?: string;
  effort?: string;
  structure?: string;
}

export function generateReport(params: GenerateParams): Promise<MonthlyReportOut> {
  return fetch(`${API_BASE_URL}/monthly-reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  }).then((r) => j(r));
}

export interface Coverage {
  period: { start: string; end: string; days: number };
  contracts: { new_awards: number; new_value: number; amendments: number; expiries: number; expiry_value: number };
  opportunities: { open_atms: number; closing_in_period: number };
  media: { total: number; by_category: Record<string, number> };
  defence_releases: number;
}

export function getCoverage(start: string, end: string): Promise<Coverage> {
  return fetch(`${API_BASE_URL}/monthly-reports/coverage?start=${start}&end=${end}`).then((r) => j(r));
}

export interface NewsDomain { domain: string; label: string | null; enabled: boolean; }

export function listDomains(): Promise<NewsDomain[]> {
  return fetch(`${API_BASE_URL}/monthly-reports/domains`).then((r) => j(r));
}

export function addDomain(domain: string): Promise<{ domain: string }> {
  return fetch(`${API_BASE_URL}/monthly-reports/domains`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain }),
  }).then((r) => j(r));
}

export function removeDomain(domain: string): Promise<{ removed: string }> {
  return fetch(`${API_BASE_URL}/monthly-reports/domains/${encodeURIComponent(domain)}`, {
    method: "DELETE",
  }).then((r) => j(r));
}

export function triggerHarvest(effort = "standard"): Promise<{ fetched: number; inserted: number; updated: number }> {
  return fetch(`${API_BASE_URL}/monthly-reports/harvest?effort=${effort}`, { method: "POST" }).then((r) => j(r));
}
