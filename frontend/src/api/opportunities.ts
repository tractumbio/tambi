import { apiGet } from "./client";

export interface AtmRow {
  atm_id: string;
  title: string | null;
  description: string | null;
  agency_name: string | null;
  atm_type: string | null;
  unspsc_code: string | null;
  unspsc_title: string | null;
  published_date: string | null;
  close_date: string | null;
  days_to_close: number | null;
  location_state: string | null;
  is_defence: boolean;
  status: string;
  url: string | null;
}

export interface AtmPage {
  total: number;
  limit: number;
  items: AtmRow[];
}

export type AtmStatus = "open" | "closed" | "all";

export interface CompetitorScore {
  slug: string;
  label: string;
  category: string;
  score: number;
  capability_signal: number;
  unspsc_signal: number;
  has_agency_relationship: boolean;
}

export interface ScoredAtmRow extends AtmRow {
  accenture_score: number;
  accenture_grade: string;
  recommendation: string;
  accenture_capability_signal: number;
  accenture_unspsc_signal: number;
  accenture_has_agency_relationship: boolean;
  competitor_scores: CompetitorScore[];
  threat_level: string;
  top_threat_slug: string | null;
}

export interface ScoredAtmPage {
  total: number;
  limit: number;
  scoring_mode: string;
  items: ScoredAtmRow[];
}

export interface AiCompetitorThreat {
  slug: string;
  label: string;
  score: number;
  reason: string;
}

export interface AiScoreResult {
  atm_id: string;
  accenture_score: number;
  grade: string;
  recommendation: string;
  rationale: string;
  win_factors: string[];
  capability_gaps: string[];
  competitor_threats: AiCompetitorThreat[];
}

export function getAtms(params?: {
  defence_only?: boolean;
  status?: AtmStatus;
  limit?: number;
}): Promise<AtmPage> {
  return apiGet<AtmPage>("/opportunities/atms", params as Record<string, string | number | boolean>);
}

export function getScoredAtms(params?: {
  defence_only?: boolean;
  status?: AtmStatus;
  limit?: number;
}): Promise<ScoredAtmPage> {
  return apiGet<ScoredAtmPage>("/opportunities/atms/scored", params as Record<string, string | number | boolean>);
}

export async function getAtmAiScore(atm_id: string): Promise<AiScoreResult> {
  const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";
  const resp = await fetch(`${API_BASE_URL}/opportunities/atms/${encodeURIComponent(atm_id)}/ai-score`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`AI score failed: ${resp.status}`);
  return resp.json() as Promise<AiScoreResult>;
}
