import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Box, Button, Card, CardContent, CircularProgress,
  Skeleton, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { getAddressableSummary, getExpiring, getGrowth, getNetworkContracts } from "../api/metrics";
import { commissionResearch } from "../api/research";
import { useApi } from "../api/useApi";
import { formatAud, formatDate } from "../lib/format";
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

// Derive contract count by year from the contracts list
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
  const [aiInsight, setAiInsight] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const depKey = `${fyWindow}|${filter?.theme ?? "all"}`;
  const accFilter = { ...filter, competitor: "accenture" };

  const summary = useApi(() => getAddressableSummary(fyWindow, accFilter), [depKey]);
  const growth = useApi(() => getGrowth(undefined, filter), [filter?.theme ?? "all"]);
  const contracts = useApi(() => getNetworkContracts(false, 500, accFilter), [filter?.theme ?? "all"]);
  const expiring = useApi(() => getExpiring(365 * 3, accFilter), [filter?.theme ?? "all"]);

  const contractsByYear = countByYear(contracts.data?.items ?? []);

  const generateInsight = async () => {
    setAiLoading(true);
    setAiInsight(null);
    try {
      const report = await commissionResearch(
        "Accenture's Position in the Australian Defence Consulting Market",
        "Analyse Accenture's overall position in the Australian Defence professional-services market. Cover: total contract value and share of the addressable market, year-on-year trends, contract pipeline (upcoming expiries and renewal risk), key agencies Accenture works with, service-offering mix, and how Accenture compares to peer firms. Provide specific strategic recommendations.",
      );
      setAiInsight(report.executive_summary + "\n\n" + report.recommendation);
    } catch {
      setAiInsight("Could not generate AI insights — please try again.");
    } finally {
      setAiLoading(false);
    }
  };

  const s = summary.data;
  const expiringItems = (expiring.data ?? []).slice(0, 12);
  const totalContracts = contracts.data?.total ?? 0;

  return (
    <Box sx={{ mt: 5 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 3, flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Accenture</Typography>
          <Typography variant="h6" sx={{ fontWeight: 800 }}>Accenture's Position</Typography>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
            Accenture's footprint, trend, and pipeline in Defence consulting.
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
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2, mb: 3 }}>
        <KpiCard
          label="Total Contract Value"
          value={formatAud(s?.accenture_value)}
          sub="Accenture Defence contracts"
          loading={summary.loading}
        />
        <KpiCard
          label="Contracts Won"
          value={contracts.loading ? "…" : String(totalContracts)}
          sub="Total Accenture contracts"
          loading={contracts.loading}
        />
        <KpiCard
          label="CAGR"
          value={growth.data?.cagr_pct != null ? `${growth.data.cagr_pct > 0 ? "+" : ""}${growth.data.cagr_pct}%` : "—"}
          sub="Addressable market growth rate"
          loading={growth.loading}
        />
      </Box>

      {/* Value by FY + Contract count side by side */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2, mb: 3 }}>
        {/* Accenture value by FY */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Accenture value by financial year</Typography>
            {growth.loading ? <Skeleton variant="rectangular" height={220} /> :
              (growth.data?.points.length ?? 0) === 0 ? <NoData /> : (
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={growth.data?.points ?? []} margin={{ top: 4, right: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="fy_label" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis yAxisId="v" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} width={52} />
                  <YAxis yAxisId="pct" orientation="right" tick={{ fontSize: 11, fill: "#98A2B3" }} tickFormatter={(v) => `${v}%`} width={36} />
                  <Tooltip
                    formatter={(v: number, n: string) => n === "yoy_pct" ? [`${v}%`, "YoY"] : [formatAud(v), n === "accenture_value" ? "Accenture" : "Market"]}
                    contentStyle={tooltipStyle}
                  />
                  <Bar yAxisId="v" dataKey="accenture_value" fill={ACCENTURE_COLOR} name="Accenture" radius={[3, 3, 0, 0]} />
                  <Line yAxisId="pct" type="monotone" dataKey="yoy_pct" stroke={SLATE} strokeWidth={1.5} dot={false} name="YoY %" />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Contracts won by year */}
        <Card elevation={0} sx={CARD_SX}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 2 }}>Number of contracts by year</Typography>
            {contracts.loading ? <Skeleton variant="rectangular" height={220} /> :
              contractsByYear.length === 0 ? <NoData /> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={contractsByYear} margin={{ top: 4, right: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="year" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis tick={{ fontSize: 11, fill: SLATE }} allowDecimals={false} />
                  <Tooltip formatter={(v: number) => [v, "Contracts"]} contentStyle={tooltipStyle} />
                  <Bar dataKey="count" name="Contracts" radius={[3, 3, 0, 0]}>
                    {contractsByYear.map((_, i) => (
                      <Cell key={i} fill={ACCENTURE_COLOR} fillOpacity={0.65 + (i / contractsByYear.length) * 0.35} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Current contracts & expiries */}
      <Card elevation={0} sx={{ ...CARD_SX, mb: 3 }}>
        <CardContent>
          <Typography sx={{ ...LABEL_SX, mb: 2 }}>
            Current contracts — expiring within 3 years
            {!expiring.loading && ` (${expiringItems.length} shown)`}
          </Typography>
          {expiring.loading ? <Skeleton variant="rectangular" height={200} /> :
            expiringItems.length === 0 ? (
              <Typography sx={{ fontSize: 13, color: INK_MUTED }}>No Accenture contracts expiring in the next 3 years.</Typography>
            ) : (
              <Box>
                {/* Column headers */}
                <Box sx={{ display: "grid", gridTemplateColumns: "2.5fr 2fr 1fr 1fr 80px", gap: 1.5, px: 1.5, py: 0.75, bgcolor: "#F9FAFB", borderRadius: 1, mb: 0.5 }}>
                  {["Contract", "Agency", "Value", "Expires", "Days"].map((h) => (
                    <Typography key={h} sx={{ fontSize: 11, fontWeight: 700, color: INK_MUTED, textTransform: "uppercase", letterSpacing: ".06em" }}>{h}</Typography>
                  ))}
                </Box>
                {expiringItems.map((c, i) => {
                  const urgent = (c.days_to_expiry ?? 999) < 90;
                  const soon = (c.days_to_expiry ?? 999) < 180;
                  return (
                    <Box key={c.ocid} sx={{
                      display: "grid", gridTemplateColumns: "2.5fr 2fr 1fr 1fr 80px", gap: 1.5,
                      px: 1.5, py: 1, borderBottom: i < expiringItems.length - 1 ? "1px solid #F3F4F6" : 0,
                      alignItems: "center", "&:hover": { bgcolor: "#FAF5FF" }, borderRadius: i === 0 ? "4px 4px 0 0" : 0,
                    }}>
                      <Typography sx={{ fontSize: 12.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.title || c.cn_id || "—"}
                      </Typography>
                      <Typography sx={{ fontSize: 12, color: INK_MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {c.buyer_name || "—"}
                      </Typography>
                      <Typography sx={{ fontSize: 12.5, fontWeight: 700 }}>{formatAud(c.value)}</Typography>
                      <Typography sx={{ fontSize: 12, color: urgent ? "#B91C1C" : soon ? "#92400E" : INK_MUTED }}>
                        {formatDate(c.period_end)}
                      </Typography>
                      <Box sx={{ bgcolor: urgent ? "#FEE2E2" : soon ? "#FEF3C7" : "#F3F4F6", borderRadius: 1, px: 1, py: 0.25, textAlign: "center" }}>
                        <Typography sx={{ fontSize: 11, fontWeight: 700, color: urgent ? "#B91C1C" : soon ? "#92400E" : INK_MUTED }}>
                          {c.days_to_expiry != null ? `${c.days_to_expiry}d` : "—"}
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            )
          }
        </CardContent>
      </Card>

      {/* AI Summary */}
      <Card elevation={0} sx={{ ...CARD_SX, borderColor: aiInsight ? ACCENTURE_COLOR : undefined, bgcolor: aiInsight ? "rgba(161,0,255,.02)" : undefined }}>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: aiInsight ? 2 : 0 }}>
            <Typography sx={LABEL_SX}>AI Strategic Summary</Typography>
            {!aiInsight && (
              <Button
                variant="outlined" size="small"
                startIcon={aiLoading ? <CircularProgress size={14} /> : <AutoAwesomeIcon />}
                disabled={aiLoading}
                onClick={generateInsight}
                sx={{ textTransform: "none", fontSize: 12.5, borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR }}
              >
                {aiLoading ? "Analysing Accenture's position…" : "Generate AI Summary"}
              </Button>
            )}
          </Box>
          {aiInsight && (
            <>
              {aiInsight.split("\n\n").map((para, i) => (
                <Typography key={i} sx={{ fontSize: 14, lineHeight: 1.75, color: "#1F2937", mb: 1.25, whiteSpace: "pre-line" }}>
                  {para}
                </Typography>
              ))}
              <Button size="small" onClick={() => { setAiInsight(null); generateInsight(); }}
                sx={{ mt: 1, textTransform: "none", fontSize: 12, color: ACCENTURE_COLOR, px: 0 }}>
                Regenerate
              </Button>
            </>
          )}
          {!aiInsight && !aiLoading && (
            <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
              Claude analyses Accenture's live contract data — value, share, trends, expiry risk, and peer comparison.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

function NoData() {
  return (
    <Box sx={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Typography sx={{ fontSize: 13, color: "#98A2B3" }}>No data for this selection</Typography>
    </Box>
  );
}
