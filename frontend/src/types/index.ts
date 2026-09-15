// Shared TypeScript types, mirroring backend Pydantic schemas.
// See backend/app/schemas/ — keep these in sync.

export interface HealthResponse {
  status: "ok";
  environment: string;
  database_mode: string;
  ai_provider: string;
}

// --- metrics (backend/app/schemas/metrics.py) ---

export interface SummaryKpis {
  period_start: string | null;
  period_end: string | null;
  total_value: number;
  contract_count: number;
  accenture_value: number;
  accenture_share: number; // 0..1
  total_value_delta_pct: number | null;
  contract_count_delta_pct: number | null;
  accenture_value_delta_pct: number | null;
}

export interface SharePoint {
  bucket: string;
  competitor_slug: string;
  competitor_label: string;
  value: number;
}

export interface ShareOverTime {
  granularity: "month" | "quarter";
  points: SharePoint[];
}

export interface ThemeBreakdownRow {
  theme_slug: string;
  theme_label: string;
  total_value: number;
  contract_count: number;
  accenture_value: number;
  field_value: number;
}

export interface CompetitorMomentumRow {
  competitor_slug: string;
  competitor_label: string;
  category: string;
  value_12m: number;
  count_12m: number;
  value_prev_12m: number;
  trend: "up" | "down" | "flat";
}

export interface ExpiringContract {
  ocid: string;
  cn_id: string | null;
  title: string | null;
  buyer_name: string | null;
  supplier_name: string | null;
  competitor_slug: string | null;
  competitor_label: string | null;
  value: number | null;
  period_end: string | null;
  days_to_expiry: number | null;
  themes: string[];
}

export interface AgencyBreakdownRow {
  agency_id: number;
  agency_name: string;
  total_value: number;
  contract_count: number;
}

export type FyWindow = "all" | "last3" | "last5" | "current";

export interface ServiceOfferingRow {
  service_offering: string;
  total_value: number;
  annualised_value: number;
  contract_count: number;
  accenture_value: number;
  field_value: number;
}

export interface AddressableSummary {
  fy_window: string;
  total_defence_value: number;
  addressable_value: number;
  addressable_annualised: number;
  addressable_count: number;
  addressable_pct_of_defence: number;
  accenture_value: number;
  accenture_share_of_addressable: number;
}

export interface GrowthPoint {
  fy_end_year: number;
  fy_label: string;
  value: number;
  accenture_value: number;
  yoy_pct: number | null;
}

export interface GrowthResponse {
  service_offering: string | null;
  points: GrowthPoint[];
  cagr_pct: number | null;
  latest_fy_value: number;
  peak_fy_label: string | null;
}

export type PeerCohort = "big4" | "mbb" | "challengers";

export interface PeerMember {
  slug: string;
  label: string;
  value: number;
  contract_count: number;
}

export interface PeerSeriesPoint {
  fy_end_year: number;
  fy_label: string;
  firms: Record<string, number>;
}

export interface PeerComparison {
  cohort: string;
  cohort_label: string;
  basis: string;
  accenture_value: number;
  accenture_count: number;
  cohort_value: number;
  cohort_count: number;
  accenture_share: number;
  members: PeerMember[];
  series: PeerSeriesPoint[];
}

export interface NetworkNode {
  id: string;
  label: string;
  kind: "competitor" | "agency" | "branch" | "theme";
  category: string | null;
  slug: string | null;
  value: number;
  contract_count: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  value: number;
  contract_count: number;
}

export interface NetworkGraphData {
  basis: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface NetworkContractRow {
  ocid: string;
  cn_id: string | null;
  title: string | null;
  description: string | null;
  supplier_name: string | null;
  competitor_slug: string | null;
  competitor_label: string | null;
  agency_name: string | null;
  buyer_division: string | null;
  buyer_branch: string | null;
  value_amount: number | null;
  value_currency: string | null;
  value_per_year: number | null;
  date_published: string | null;
  date_signed: string | null;
  period_start: string | null;
  period_end: string | null;
  procurement_method: string | null;
  unspsc_code: string | null;
  is_addressable: boolean;
  service_offering: string | null;
  service_offering_confidence: number | null;
  amendment_count: number;
  themes: string[];
}

export interface NetworkContracts {
  total: number;
  limit: number;
  items: NetworkContractRow[];
}

// --- contracts (backend/app/schemas/contracts.py) ---

export interface ContractListItem {
  ocid: string;
  cn_id: string | null;
  title: string | null;
  buyer_name: string | null;
  supplier_name: string | null;
  competitor_slug: string | null;
  competitor_label: string | null;
  value_amount: number | null;
  value_currency: string | null;
  date_published: string | null;
  period_end: string | null;
  procurement_method: string | null;
  is_defence: boolean;
  themes: string[];
}

export interface ContractPage {
  items: ContractListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ThemeOption {
  slug: string;
  label: string;
}

export interface CompetitorOption {
  slug: string;
  label: string;
  category: string;
}

export interface AgencyOption {
  id: number;
  name: string;
}

export interface FilterOptions {
  themes: ThemeOption[];
  competitors: CompetitorOption[];
  agencies: AgencyOption[];
  value_range: { min: number | null; max: number | null };
  date_range: { min: string | null; max: string | null };
}

export interface CommonFilterParams {
  theme?: string;
  competitor?: string;
  agency_id?: number;
  date_from?: string;
  date_to?: string;
  min_value?: number;
  max_value?: number;
}
