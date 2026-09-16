import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Box, Card, CardContent, Skeleton, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import { getAddressableSummary, getExpiring, getGrowth, getNetworkContracts } from "../api/metrics";
import { useApi } from "../api/useApi";
import { formatAud } from "../lib/format";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, LABEL_SX, tooltipStyle } from "../theme/dashboardStyles";
import type { CommonFilterParams, FyWindow } from "../types";

const GRID = "#E7ECF3";
const SLATE = "#526070";

const FY_WINDOWS: { value: FyWindow; label: string }[] = [
  { value: "all", label: "All FY" },
  { value: "last5", label: "Last 5" },
  { value: "last3", label: "Last 3" },
];

function countByYear(items: { date_published: string | null }[]): { year: string; count: number }[] {
  const map: Record<string, number> = {};
  for (const c of items) {
    if (!c.date_published) continue;
    const yr = c.date_published.slice(0, 4);
    map[yr] = (map[yr] ?? 0) + 1;
  }
  return Object.entries(map).sort(([a], [b]) => a.localeCompare(b)).map(([year, count]) => ({ year, count }));
}

function KpiCard({ label, value, sub, loading }: { label: string; value: string; sub: string; loading?: boolean }) {
  return (
    <Card elevation={0} sx={CARD_SX}>
      <CardContent sx={{ p: "17px !important" }}>
        <Typography sx={{ ...LABEL_SX, mb: 1 }}>{label}</Typography>
        {loading ? <Skeleton width={110} height={36} /> : (
          <Typography sx={{ fontSize: 28, fontWeight: 800, letterSpacing: "-.02em", lineHeight: 1.05, color: ACCENTURE_COLOR, fontVariantNumeric: "tabular-nums" }}>
            {value}
          </Typography>
        )}
        <Typography sx={{ fontSize: 12, color: INK_MUTED, mt: 0.75 }}>{sub}</Typography>
      </CardContent>
    </Card>
  );
}

export function AccenturePosition({ filter }: { filter?: CommonFilterParams }) {
  const [fyWindow, setFyWindow] = useState<FyWindow>("last5");

  const depKey = `${fyWindow}|${filter?.theme ?? "all"}`;
  const accFilter = { ...filter, competitor: "accenture" };

  const summary = useApi(() => getAddressableSummary(fyWindow, accFilter), [depKey]);
  const growth = useApi(() => getGrowth(undefined, filter), [filter?.theme ?? "all"]);
  const contracts = useApi(() => getNetworkContracts(false, 500, accFilter), [filter?.theme ?? "all"]);
  const current = useApi(() => getExpiring(365 * 10, accFilter), [filter?.theme ?? "all"]);

  const contractsByYear = countByYear(contracts.data?.items ?? []);
  const currentValue = (current.data ?? []).reduce((s, c) => s + (c.value ?? 0), 0);
  const currentCount = current.data?.length ?? 0;

  return (
    <Box sx={{ mt: 5 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 3, flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Accenture</Typography>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Accenture's Position</Typography>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
            Accenture's footprint and trend in Defence consulting.
          </Typography>
        </Box>
        <ToggleButtonGroup
          size="small" exclusive value={fyWindow}
          onChange={(_, v) => v && setFyWindow(v)}
          sx={{ "& .MuiToggleButton-root.Mui-selected": { color: ACCENTURE_COLOR, borderColor: ACCENTURE_COLOR } }}
        >
          {FY_WINDOWS.map((w) => (
            <ToggleButton key={w.value} value={w.value} sx={{ fontSize: 12, py: 0.4, textTransform: "none" }}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      {/* KPI row */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, mb: 3 }}>
        <KpiCard
          label="Total Contract Value"
          value={formatAud(summary.data?.accenture_value)}
          sub="All Accenture Defence contracts"
          loading={summary.loading}
        />
        <KpiCard
          label="Total Contracts"
          value={contracts.loading ? "…" : String(contracts.data?.total ?? 0)}
          sub="Accenture contracts on record"
          loading={contracts.loading}
        />
        <KpiCard
          label="Current Contracts Value"
          value={current.loading ? "…" : formatAud(currentValue)}
          sub="Value of active contracts"
          loading={current.loading}
        />
        <KpiCard
          label="Current Contracts"
          value={current.loading ? "…" : String(currentCount)}
          sub="Active contracts not yet expired"
          loading={current.loading}
        />
      </Box>

      {/* Charts row */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
        {/* Annualised contract value per FY */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Annualised contract value · by financial year</Typography>
            {growth.loading ? <Skeleton variant="rectangular" height={240} /> :
              (growth.data?.points.length ?? 0) === 0 ? <NoData /> : (
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={growth.data?.points ?? []} margin={{ top: 4, right: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="fy_label" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis yAxisId="v" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} width={56} />
                  <YAxis yAxisId="pct" orientation="right" tick={{ fontSize: 11, fill: "#98A2B3" }} tickFormatter={(v) => `${v}%`} width={36} />
                  <Tooltip
                    formatter={(v: number, n: string) => n === "yoy_pct" ? [`${v}%`, "YoY"] : [formatAud(v), "Accenture"]}
                    contentStyle={tooltipStyle}
                  />
                  <Bar yAxisId="v" dataKey="accenture_value" fill={ACCENTURE_COLOR} name="Accenture" radius={[3, 3, 0, 0]} />
                  <Line yAxisId="pct" type="monotone" dataKey="yoy_pct" stroke={SLATE} strokeWidth={1.5} dot={false} name="YoY %" />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Number of contracts per FY (by published year) */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Number of contracts · by year</Typography>
            {contracts.loading ? <Skeleton variant="rectangular" height={240} /> :
              contractsByYear.length === 0 ? <NoData /> : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={contractsByYear} margin={{ top: 4, right: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="year" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis tick={{ fontSize: 11, fill: SLATE }} allowDecimals={false} />
                  <Tooltip formatter={(v: number) => [v, "Contracts"]} contentStyle={tooltipStyle} />
                  <Bar dataKey="count" name="Contracts" radius={[3, 3, 0, 0]}>
                    {contractsByYear.map((_, i) => (
                      <Cell key={i} fill={ACCENTURE_COLOR} fillOpacity={0.6 + (i / contractsByYear.length) * 0.4} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}

function NoData() {
  return (
    <Box sx={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Typography sx={{ fontSize: 13, color: "#98A2B3" }}>No data for this selection</Typography>
    </Box>
  );
}
