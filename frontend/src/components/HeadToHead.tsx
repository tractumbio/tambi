import { useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Box, Card, CardContent,
  FormControl, MenuItem, Select, Skeleton, Typography,
} from "@mui/material";
import { getShareOverTime, getCompetitorMomentum, getByTheme, getNetworkContracts } from "../api/metrics";
import { getFilters } from "../api/contracts";
import { useApi } from "../api/useApi";
import { formatAud } from "../lib/format";
import { ACCENTURE_COLOR, competitorColor } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, LABEL_SX, tooltipStyle } from "../theme/dashboardStyles";
import { InfoTooltip } from "./InfoTooltip";
import type { CommonFilterParams } from "../types";

const GRID = "#E7ECF3";
const SLATE = "#526070";

// ── duration bucketing ────────────────────────────────────────────────────────
function durationBuckets(contracts: { period_start: string | null; period_end: string | null }[]): Record<string, number> {
  const buckets: Record<string, number> = { "0–12m": 0, "12–24m": 0, "24–36m": 0, "36–60m": 0, "60m+": 0 };
  for (const c of contracts) {
    if (!c.period_start || !c.period_end) continue;
    const months = (new Date(c.period_end).getTime() - new Date(c.period_start).getTime()) / (1000 * 60 * 60 * 24 * 30);
    if (months < 0) continue;
    if (months < 12) buckets["0–12m"]++;
    else if (months < 24) buckets["12–24m"]++;
    else if (months < 36) buckets["24–36m"]++;
    else if (months < 60) buckets["36–60m"]++;
    else buckets["60m+"]++;
  }
  return buckets;
}

function avgDuration(contracts: { period_start: string | null; period_end: string | null }[]): number | null {
  const valid = contracts
    .filter((c) => c.period_start && c.period_end)
    .map((c) => (new Date(c.period_end!).getTime() - new Date(c.period_start!).getTime()) / (1000 * 60 * 60 * 24 * 30));
  if (valid.length === 0) return null;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

// ── KPI tile ─────────────────────────────────────────────────────────────────
function KpiTile({ label, a, b, fmtA, fmtB, colorA, colorB }: {
  label: string; a: string; b: string; fmtA?: string; fmtB?: string; colorA: string; colorB: string;
}) {
  return (
    <Box sx={{ ...CARD_SX, p: 2, flex: 1, minWidth: 160 }}>
      <Typography sx={{ ...LABEL_SX, mb: 1.5 }}>{label}</Typography>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
        <Box>
          <Typography sx={{ fontSize: 20, fontWeight: 800, color: colorA }}>{a}</Typography>
          {fmtA && <Typography sx={{ fontSize: 10, color: INK_MUTED }}>{fmtA}</Typography>}
        </Box>
        <Box sx={{ textAlign: "right" }}>
          <Typography sx={{ fontSize: 20, fontWeight: 800, color: colorB }}>{b}</Typography>
          {fmtB && <Typography sx={{ fontSize: 10, color: INK_MUTED, textAlign: "right" }}>{fmtB}</Typography>}
        </Box>
      </Box>
    </Box>
  );
}

// ── main component ────────────────────────────────────────────────────────────
export function HeadToHead({ filter }: { filter?: CommonFilterParams }) {
  const [firmA, setFirmA] = useState("accenture");
  const [firmB, setFirmB] = useState("kpmg");

  const filters = useApi(getFilters, []);
  const shareOverTime = useApi(() => getShareOverTime("quarter", filter), [filter?.theme ?? ""]);
  const momentum = useApi(() => getCompetitorMomentum(filter), [filter?.theme ?? ""]);
  const themesA = useApi(() => getByTheme({ ...filter, competitor: firmA }), [firmA, filter?.theme ?? ""]);
  const themesB = useApi(() => getByTheme({ ...filter, competitor: firmB }), [firmB, filter?.theme ?? ""]);
  const contractsA = useApi(() => getNetworkContracts(false, 400, { ...filter, competitor: firmA }), [firmA, filter?.theme ?? ""]);
  const contractsB = useApi(() => getNetworkContracts(false, 400, { ...filter, competitor: firmB }), [firmB, filter?.theme ?? ""]);

  const competitors = useMemo(
    () => filters.data?.competitors ?? [],
    [filters.data],
  );

  // Value-over-time series (pivot from flat points)
  const valueSeries = useMemo(() => {
    if (!shareOverTime.data) return [];
    const buckets: Record<string, Record<string, number>> = {};
    for (const p of shareOverTime.data.points) {
      if (p.competitor_slug !== firmA && p.competitor_slug !== firmB) continue;
      if (!buckets[p.bucket]) buckets[p.bucket] = {};
      buckets[p.bucket][p.competitor_slug] = (buckets[p.bucket][p.competitor_slug] ?? 0) + p.value;
    }
    return Object.entries(buckets).map(([bucket, vals]) => ({ bucket, [firmA]: vals[firmA] ?? 0, [firmB]: vals[firmB] ?? 0 }));
  }, [shareOverTime.data, firmA, firmB]);

  // Momentum for the two firms
  const momA = useMemo(() => momentum.data?.find((m) => m.competitor_slug === firmA), [momentum.data, firmA]);
  const momB = useMemo(() => momentum.data?.find((m) => m.competitor_slug === firmB), [momentum.data, firmB]);

  // Theme comparison (merge both firms' byTheme data)
  const themeChart = useMemo(() => {
    if (!themesA.data || !themesB.data) return [];
    const map: Record<string, { label: string; a: number; b: number }> = {};
    for (const t of themesA.data) map[t.theme_slug] = { label: t.theme_label, a: t.total_value, b: 0 };
    for (const t of themesB.data) {
      if (!map[t.theme_slug]) map[t.theme_slug] = { label: t.theme_label, a: 0, b: 0 };
      map[t.theme_slug].b = t.total_value;
    }
    return Object.values(map)
      .filter((r) => r.a > 0 || r.b > 0)
      .sort((x, y) => (y.a + y.b) - (x.a + x.b))
      .slice(0, 10);
  }, [themesA.data, themesB.data]);

  // Duration distribution
  const durChartData = useMemo(() => {
    const bA = contractsA.data ? durationBuckets(contractsA.data.items) : {};
    const bB = contractsB.data ? durationBuckets(contractsB.data.items) : {};
    return ["0–12m", "12–24m", "24–36m", "36–60m", "60m+"].map((b) => ({
      bucket: b, [firmA]: bA[b] ?? 0, [firmB]: bB[b] ?? 0,
    }));
  }, [contractsA.data, contractsB.data, firmA, firmB]);

  const avgA = useMemo(() => avgDuration(contractsA.data?.items ?? []), [contractsA.data]);
  const avgB = useMemo(() => avgDuration(contractsB.data?.items ?? []), [contractsB.data]);

  const labelFor = (slug: string) => competitors.find((c) => c.slug === slug)?.label ?? slug;
  const colorA = competitorColor(firmA);
  const colorB = competitorColor(firmB);

  const loading = shareOverTime.loading || momentum.loading;

  return (
    <Box sx={{ mt: 5 }}>
      {/* Header + selectors */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 3, flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Head-to-Head</Typography>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Typography variant="h6" sx={{ fontWeight: 800 }}>Firm Comparison</Typography>
            <InfoTooltip text="Pulls rolling 12-month contract values and quarterly trends for any two selected firms directly from the AusTender warehouse. Theme coverage shows which Defence capability areas each firm targets." />
          </Box>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
            Contract value, count, duration, and theme coverage — two firms side by side.
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
          <FirmSelect value={firmA} onChange={setFirmA} options={competitors} color={colorA} />
          <Typography sx={{ fontSize: 13, fontWeight: 700, color: INK_MUTED }}>vs</Typography>
          <FirmSelect value={firmB} onChange={setFirmB} options={competitors} color={colorB} />
        </Box>
      </Box>

      {/* KPI row */}
      <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
        <KpiTile
          label="12-month value"
          a={momA ? formatAud(momA.value_12m) : "—"}
          b={momB ? formatAud(momB.value_12m) : "—"}
          fmtA={labelFor(firmA)} fmtB={labelFor(firmB)}
          colorA={colorA} colorB={colorB}
        />
        <KpiTile
          label="12-month contracts"
          a={momA ? String(momA.count_12m) : "—"}
          b={momB ? String(momB.count_12m) : "—"}
          fmtA={labelFor(firmA)} fmtB={labelFor(firmB)}
          colorA={colorA} colorB={colorB}
        />
        <KpiTile
          label="Avg contract length"
          a={avgA != null ? `${avgA.toFixed(0)}m` : "—"}
          b={avgB != null ? `${avgB.toFixed(0)}m` : "—"}
          fmtA={labelFor(firmA)} fmtB={labelFor(firmB)}
          colorA={colorA} colorB={colorB}
        />
        <KpiTile
          label="Trend (12m)"
          a={momA ? (momA.trend === "up" ? "▲ Up" : momA.trend === "down" ? "▼ Down" : "→ Flat") : "—"}
          b={momB ? (momB.trend === "up" ? "▲ Up" : momB.trend === "down" ? "▼ Down" : "→ Flat") : "—"}
          colorA={colorA} colorB={colorB}
        />
      </Box>

      {/* Value over time */}
      <Card elevation={0} sx={{ ...CARD_SX, mb: 2 }}>
        <CardContent>
          <Typography sx={{ ...LABEL_SX, mb: 2 }}>Contract value over time</Typography>
          {loading ? <Skeleton variant="rectangular" height={220} /> : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={valueSeries} margin={{ top: 4, right: 12, left: 8 }}>
                <defs>
                  <linearGradient id="gradA" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colorA} stopOpacity={0.18} />
                    <stop offset="95%" stopColor={colorA} stopOpacity={0.01} />
                  </linearGradient>
                  <linearGradient id="gradB" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colorB} stopOpacity={0.18} />
                    <stop offset="95%" stopColor={colorB} stopOpacity={0.01} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: SLATE }} />
                <YAxis tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} width={56} />
                <Tooltip formatter={(v: number, n: string) => [formatAud(v), n === firmA ? labelFor(firmA) : labelFor(firmB)]} contentStyle={tooltipStyle} />
                <Legend formatter={(v) => v === firmA ? labelFor(firmA) : labelFor(firmB)} />
                <Area type="monotone" dataKey={firmA} stroke={colorA} strokeWidth={2.5} fill="url(#gradA)" dot={false} />
                <Area type="monotone" dataKey={firmB} stroke={colorB} strokeWidth={2} fill="url(#gradB)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Theme + Duration charts side by side */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 2, mb: 2 }}>
        {/* Theme mapping */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Defence theme coverage</Typography>
            {themesA.loading || themesB.loading ? <Skeleton variant="rectangular" height={280} /> : (
              <ResponsiveContainer width="100%" height={Math.max(280, themeChart.length * 32)}>
                <BarChart layout="vertical" data={themeChart} margin={{ left: 8, right: 12 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} />
                  <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 10, fill: "#374151" }} />
                  <Tooltip formatter={(v: number, n: string) => [formatAud(v), n === "a" ? labelFor(firmA) : labelFor(firmB)]} contentStyle={tooltipStyle} />
                  <Legend formatter={(v) => v === "a" ? labelFor(firmA) : labelFor(firmB)} />
                  <Bar dataKey="a" fill={colorA} radius={[0, 3, 3, 0]} />
                  <Bar dataKey="b" fill={colorB} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Duration distribution */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Contract length distribution</Typography>
            {contractsA.loading || contractsB.loading ? <Skeleton variant="rectangular" height={280} /> : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={durChartData} margin={{ top: 4, right: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis tick={{ fontSize: 11, fill: SLATE }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle}
                    formatter={(v: number, n: string) => [v, n === firmA ? labelFor(firmA) : labelFor(firmB)]} />
                  <Legend formatter={(v) => v === firmA ? labelFor(firmA) : labelFor(firmB)} />
                  <Bar dataKey={firmA} fill={colorA} radius={[3, 3, 0, 0]} />
                  <Bar dataKey={firmB} fill={colorB} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </Box>

    </Box>
  );
}

function FirmSelect({ value, onChange, options, color }: {
  value: string;
  onChange: (v: string) => void;
  options: { slug: string; label: string }[];
  color: string;
}) {
  return (
    <FormControl size="small">
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        sx={{ fontSize: 13, minWidth: 160, bgcolor: "#fff", "& .MuiSelect-select": { color } }}
        renderValue={(v) => (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color }} />
            {options.find((o) => o.slug === v)?.label ?? v}
          </Box>
        )}
      >
        {options.map((o) => (
          <MenuItem key={o.slug} value={o.slug} sx={{ fontSize: 13 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: competitorColor(o.slug) }} />
              {o.label}
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
