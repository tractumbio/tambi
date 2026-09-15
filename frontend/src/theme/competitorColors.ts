// Palette lifted from the previous-analytics static dashboards so the React app
// reads as the same product. Accenture is always the purple accent; competitors use
// their brand colours; service offerings use a purple sequential ramp.

export const ACCENTURE_COLOR = "#A100FF";

// Brand-accurate competitor colours (from DefenceTAM.py / CompareDashboard.py).
export const COMPETITOR_COLORS: Record<string, string> = {
  accenture: ACCENTURE_COLOR,
  deloitte: "#86BC25",
  kpmg: "#00338D",
  ey: "#FFE600",
  pwc: "#E0301E",
  ibm: "#1F70C1",
  leidos: "#667785",
  dxc: "#5F259F",
  "lockheed-martin": "#0033A0",
  "bae-systems": "#00205B",
  thales: "#00A1E0",
  "boeing-defence": "#1D1D1B",
  babcock: "#005EB8",
  kbr: "#00263A",
  jacobs: "#0033A1",
  "nova-systems": "#E4002B",
  other: "#B8BEC9",
};

export function competitorColor(slug: string | null | undefined): string {
  if (!slug) return COMPETITOR_COLORS.other;
  return COMPETITOR_COLORS[slug] ?? COMPETITOR_COLORS.other;
}

// Service-offering purple ramp (from build_master.py capability_colours).
export const SERVICE_OFFERING_COLORS: Record<string, string> = {
  "Strategy, Transformation & Advisory": "#4C1D95",
  "SI & Engineering": "#6D28D9",
  "Cloud Infrastructure & Cyber": "#8B5CF6",
  "Managed Services & Operations": "#A78BFA",
  "Data, AI & Automation": "#C4B5FD",
};

export function offeringColor(name: string | null | undefined): string {
  if (!name) return "#DDD6FE";
  return SERVICE_OFFERING_COLORS[name] ?? "#7F56D9";
}

// Addressable-market donut/stack colours (from DefenceTAM.py).
export const ADDRESSABLE = "#4C1D95"; // addressable TAM
export const NOT_ADDRESSABLE = "#D8CCF3";
export const ACCENTURE_WINS = "#9F7AEA";
export const COMPETITOR_MARKET = "#5B21B6";

// Chart ink (navy titles, muted slate axes/labels) shared across all charts.
export const CHART_NAVY = "#0B2545";
export const CHART_SLATE = "#526070";
export const CHART_GRID = "#E7ECF3";
export const FIELD_GREY = "#D7DEE9";
