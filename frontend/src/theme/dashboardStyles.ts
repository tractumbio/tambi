// Shared card/label/chart styling ported from the static dashboards' CSS
// (DefenceTAM.py <style>): white cards, 14px radius, hairline border, soft shadow,
// uppercase slate titles, navy/slate chart ink.

import { CHART_GRID, CHART_SLATE } from "./competitorColors";

export const PAGE_BG = "#f6f8fb";
export const CARD_BORDER = "#e5e7eb";
export const INK = "#111827";
export const INK_MUTED = "#667085";

// .card
export const CARD_SX = {
  bgcolor: "#ffffff",
  border: `1px solid ${CARD_BORDER}`,
  borderRadius: "14px",
  boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
} as const;

// .card-title
export const LABEL_SX = {
  fontSize: 12,
  textTransform: "uppercase" as const,
  letterSpacing: ".04em",
  color: INK_MUTED,
  fontWeight: 600,
} as const;

// .card-value (Arial Black in the original → heavy weight here)
export const VALUE_SX = {
  fontSize: 30,
  fontWeight: 800,
  letterSpacing: "-.02em",
  lineHeight: 1.05,
  color: INK,
  fontVariantNumeric: "tabular-nums" as const,
} as const;

// Recharts axis/grid props for a consistent look across every chart.
export const axisTick = { fontSize: 11, fill: CHART_SLATE } as const;
export const gridProps = { strokeDasharray: "2 4", stroke: CHART_GRID } as const;
export const tooltipStyle = {
  fontSize: 12,
  borderRadius: 10,
  border: `1px solid ${CARD_BORDER}`,
  boxShadow: "0 4px 14px rgba(11,37,69,0.10)",
} as const;
