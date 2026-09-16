import { useState, type ReactNode } from "react";
import {
  Box, Card, CardContent, MenuItem, Select, Skeleton,
  ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import {
  Bar, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getAddressableSummary, getGrowth, getServiceOfferings } from "../api/metrics";
import { useApi } from "../api/useApi";
import { formatAud, formatPct } from "../lib/format";
import { ACCENTURE_COLOR, ADDRESSABLE, offeringColor } from "../theme/competitorColors";
import { CARD_SX, INK, INK_MUTED, LABEL_SX, tooltipStyle } from "../theme/dashboardStyles";
import { InfoTooltip } from "./InfoTooltip";
import type { CommonFilterParams, FyWindow } from "../types";

const GRID = "#E7ECF3";
const SLATE = "#526070";

const FY_WINDOWS: { value: FyWindow; label: string }[] = [
  { value: "all", label: "All FY" },
  { value: "last5", label: "Last 5" },
  { value: "last3", label: "Last 3" },
  { value: "current", label: "Current" },
];

function Panel({ title, action, children }: {
  title: string; action?: ReactNode; children: ReactNode;
}) {
  return (
    <Card elevation={0} sx={CARD_SX}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography sx={LABEL_SX}>{title}</Typography>
          {action}
        </Box>
        {children}
      </CardContent>
    </Card>
  );
}

export function AddressableMarket({ filter }: { filter?: CommonFilterParams }) {
  const [fyWindow, setFyWindow] = useState<FyWindow>("last5");
  const [offering, setOffering] = useState<string>("");
  const depKey = `${fyWindow}|${filter?.theme ?? "all"}`;

  const summary = useApi(() => getAddressableSummary(fyWindow, filter), [depKey]);
  const offerings = useApi(() => getServiceOfferings(fyWindow, filter), [depKey]);
  const growth = useApi(
    () => getGrowth(offering || undefined, filter),
    [offering, filter?.theme ?? "all"],
  );

  const s = summary.data;

  return (
    <Box sx={{ mt: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>
            Market Overview
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center" }}>
            <Typography variant="h6">Defence Expenditure on Consulting</Typography>
            <InfoTooltip text="Aggregates all AusTender awards to professional-services firms across 5 years. Values annualised by contract duration; service-offering tagged by keyword matching." />
          </Box>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
            The addressable professional-services slice of the Australian Defence market.
          </Typography>
        </Box>
        <ToggleButtonGroup
          size="small" exclusive value={fyWindow}
          onChange={(_, v) => v && setFyWindow(v)}
          sx={{ "& .MuiToggleButton-root.Mui-selected": { color: ACCENTURE_COLOR, borderColor: ACCENTURE_COLOR } }}
        >
          {FY_WINDOWS.map((w) => (
            <ToggleButton key={w.value} value={w.value} sx={{ fontSize: 12, py: .4, textTransform: "none" }}>
              {w.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      {/* Market KPI tiles — market-level only, no Accenture numbers here */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2, mb: 2 }}>
        {[
          { label: "Addressable Market", value: formatAud(s?.addressable_value), sub: "Total consulting contract value" },
          { label: "Annualised Run Rate", value: formatAud(s?.addressable_annualised), sub: "Current market size per year" },
          { label: "Share of All Defence", value: s ? formatPct(s.addressable_pct_of_defence) : "—", sub: "Consulting ÷ total Defence spend" },
        ].map((k) => (
          <Card key={k.label} elevation={0} sx={CARD_SX}>
            <CardContent sx={{ p: "17px !important" }}>
              <Typography sx={{ ...LABEL_SX, mb: 1 }}>{k.label}</Typography>
              {summary.loading ? <Skeleton width={110} height={36} /> : (
                <Typography sx={{ fontSize: 28, fontWeight: 800, letterSpacing: "-.02em", lineHeight: 1.05, color: INK, fontVariantNumeric: "tabular-nums" }}>
                  {k.value}
                </Typography>
              )}
              <Typography sx={{ fontSize: 12, color: INK_MUTED, mt: .75 }}>{k.sub}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
        {/* Service-offering breakdown — market total, no Accenture */}
        <Panel title="Market Value by Service Offering">
          {offerings.loading ? <Skeleton variant="rectangular" height={280} /> :
            (offerings.data?.length ?? 0) === 0 ? <Empty /> : (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart layout="vertical" data={offerings.data ?? []} margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={GRID} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} />
                <YAxis type="category" dataKey="service_offering" width={130}
                  tick={{ fontSize: 10, fill: INK }} tickFormatter={(v) => shortOffering(String(v))} />
                <Tooltip formatter={(v: number) => [formatAud(v), "Market"]} contentStyle={tooltipStyle} />
                <Bar dataKey="total_value" name="Market">
                  {(offerings.data ?? []).map((o) => (
                    <Cell key={o.service_offering} fill={offeringColor(o.service_offering)} fillOpacity={0.75} />
                  ))}
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </Panel>

        {/* Growth over FY */}
        <Panel
          title="Consulting Market Growth · annualised, by FY"
          action={
            <Select
              size="small" value={offering} displayEmpty
              onChange={(e) => setOffering(e.target.value)}
              sx={{ fontSize: 12, minWidth: 150, bgcolor: "#fff" }}
            >
              <MenuItem value="" sx={{ fontSize: 12 }}><em>All offerings</em></MenuItem>
              {(offerings.data ?? []).map((o) => (
                <MenuItem key={o.service_offering} value={o.service_offering} sx={{ fontSize: 12 }}>
                  {shortOffering(o.service_offering)}
                </MenuItem>
              ))}
            </Select>
          }
        >
          {growth.loading ? <Skeleton variant="rectangular" height={260} /> :
            (growth.data?.points.length ?? 0) === 0 ? <Empty /> : (
            <>
              <Box sx={{ display: "flex", gap: 3, mb: 1 }}>
                <Metric label="CAGR" value={growth.data?.cagr_pct != null ? `${growth.data.cagr_pct > 0 ? "+" : ""}${growth.data.cagr_pct}%` : "—"} />
                <Metric label="Latest FY" value={formatAud(growth.data?.latest_fy_value)} />
                <Metric label="Peak FY" value={growth.data?.peak_fy_label ?? "—"} />
              </Box>
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={growth.data?.points ?? []} margin={{ top: 8, right: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                  <XAxis dataKey="fy_label" tick={{ fontSize: 11, fill: SLATE }} />
                  <YAxis yAxisId="v" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} width={52} />
                  <YAxis yAxisId="y" orientation="right" tick={{ fontSize: 11, fill: "#98A2B3" }} tickFormatter={(v) => `${v}%`} width={40} />
                  <Tooltip
                    formatter={(v: number, n: string) =>
                      n === "yoy_pct" ? [`${v}%`, "YoY"] : [formatAud(v), n === "accenture_value" ? "Accenture" : "Addressable"]}
                    contentStyle={tooltipStyle} />
                  <Bar yAxisId="v" dataKey="value" fill={ADDRESSABLE} fillOpacity={0.85} name="Market" />
                  <Line yAxisId="y" type="monotone" dataKey="yoy_pct" stroke={SLATE} strokeWidth={1.5} dot={false} name="YoY %" />
                </ComposedChart>
              </ResponsiveContainer>
            </>
          )}
        </Panel>
      </Box>
    </Box>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography sx={{ ...LABEL_SX, fontSize: 10 }}>{label}</Typography>
      <Typography sx={{ fontSize: 16, fontWeight: 800, fontVariantNumeric: "tabular-nums", color: INK }}>{value}</Typography>
    </Box>
  );
}

function Empty() {
  return (
    <Box sx={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center", color: "#98A2B3" }}>
      <Typography sx={{ fontSize: 13 }}>No addressable contracts for this selection</Typography>
    </Box>
  );
}

function shortOffering(name: string): string {
  const map: Record<string, string> = {
    "Strategy, Transformation & Advisory": "Strategy & Advisory",
    "SI & Engineering": "SI & Engineering",
    "Cloud Infrastructure & Cyber": "Cloud & Cyber",
    "Managed Services & Operations": "Managed Services",
    "Data, AI & Automation": "Data, AI & Automation",
  };
  return map[name] ?? name;
}
