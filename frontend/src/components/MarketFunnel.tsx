import type { ReactNode } from "react";
import { Box, Card, CardContent, Skeleton, Typography } from "@mui/material";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { getAddressableSummary, getServiceOfferings } from "../api/metrics";
import { useApi } from "../api/useApi";
import { formatAud, formatPct } from "../lib/format";
import {
  ACCENTURE_COLOR, ACCENTURE_WINS, ADDRESSABLE, CHART_NAVY, COMPETITOR_MARKET,
  NOT_ADDRESSABLE, offeringColor,
} from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, tooltipStyle } from "../theme/dashboardStyles";
import type { CommonFilterParams, FyWindow } from "../types";

interface Slice { name: string; value: number; color: string }

function Donut({ title, subtitle, centreValue, centreLabel, slices, loading }: {
  title: string; subtitle: string; centreValue: string; centreLabel: string;
  slices: Slice[]; loading: boolean;
}) {
  return (
    <Box sx={{ flex: 1, minWidth: 0, textAlign: "center" }}>
      <Typography sx={{ fontSize: 15, fontWeight: 800, color: CHART_NAVY }}>{title}</Typography>
      <Typography sx={{ fontSize: 12, color: INK_MUTED, mb: 1 }}>{subtitle}</Typography>
      <Box sx={{ position: "relative", height: 230 }}>
        {loading ? <Skeleton variant="circular" width={210} height={210} sx={{ mx: "auto" }} /> : (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={slices} dataKey="value" nameKey="name"
                  innerRadius="68%" outerRadius="95%" startAngle={90} endAngle={-270}
                  stroke="#fff" strokeWidth={1} isAnimationActive={false}
                >
                  {slices.map((s) => <Cell key={s.name} fill={s.color} />)}
                </Pie>
                <Tooltip formatter={(v: number, n: string) => [formatAud(v), n]} contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
            <Box sx={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", pointerEvents: "none",
            }}>
              <Typography sx={{ fontSize: 26, fontWeight: 800, color: CHART_NAVY, fontVariantNumeric: "tabular-nums" }}>
                {centreValue}
              </Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED, maxWidth: 110 }}>{centreLabel}</Typography>
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}

function Step({ pct, label, value }: { pct: string; label: string; value: string }): ReactNode {
  return (
    <Box sx={{ flex: "0 0 112px", textAlign: "center", color: ACCENTURE_COLOR, alignSelf: "center" }}>
      <Typography sx={{ fontSize: 16, fontWeight: 800, lineHeight: 1.1 }}>{pct}</Typography>
      <Typography sx={{ fontSize: 11 }}>{label}</Typography>
      <Typography sx={{ fontSize: 13, fontWeight: 800 }}>{value}</Typography>
      <Box sx={{ fontSize: 22, lineHeight: 1 }}>→</Box>
    </Box>
  );
}

/** Three-step funnel: all Defence procurement → addressable market (TAM) → Accenture wins. */
export function MarketFunnel({ filter, fyWindow = "last5" }: {
  filter?: CommonFilterParams; fyWindow?: FyWindow;
}) {
  const depKey = `${fyWindow}|${filter?.theme ?? "all"}`;
  const summary = useApi(() => getAddressableSummary(fyWindow, filter), [depKey]);
  const offerings = useApi(() => getServiceOfferings(fyWindow, filter), [depKey]);

  const s = summary.data;
  const total = s?.total_defence_value ?? 0;
  const tam = s?.addressable_value ?? 0;
  const wins = s?.accenture_value ?? 0;

  const tier1: Slice[] = [
    { name: "Addressable", value: tam, color: ADDRESSABLE },
    { name: "Not addressable", value: Math.max(total - tam, 0), color: NOT_ADDRESSABLE },
  ];
  const tier2: Slice[] = [
    { name: "Accenture wins", value: wins, color: ACCENTURE_WINS },
    { name: "Rest of addressable market", value: Math.max(tam - wins, 0), color: COMPETITOR_MARKET },
  ];
  const tier3: Slice[] = [...(offerings.data ?? [])]
    .filter((o) => o.accenture_value > 0)
    .sort((a, b) => b.accenture_value - a.accenture_value)
    .map((o) => ({ name: o.service_offering, value: o.accenture_value, color: offeringColor(o.service_offering) }));

  return (
    <Card elevation={0} sx={{ ...CARD_SX, mb: 3 }}>
      <CardContent sx={{ display: "flex", alignItems: "stretch", gap: 1, flexWrap: { xs: "wrap", md: "nowrap" } }}>
        <Donut
          title="1. Total Defence Procurement Market" subtitle="Out of total Defence procurement"
          centreValue={formatAud(total)} centreLabel="Total Defence Procurement"
          slices={tier1} loading={summary.loading}
        />
        <Step pct={s ? formatPct(s.addressable_pct_of_defence) : "—"} label="Addressable to Accenture" value={formatAud(tam)} />
        <Donut
          title="2. Within Addressable Market (TAM)" subtitle="Breakdown of addressable TAM"
          centreValue={formatAud(tam)} centreLabel="Addressable Market (TAM)"
          slices={tier2} loading={summary.loading}
        />
        <Step pct={s ? formatPct(s.accenture_share_of_addressable) : "—"} label="Accenture wins" value={formatAud(wins)} />
        <Donut
          title="3. Breakdown of Accenture Wins" subtitle="Distribution across service offerings"
          centreValue={formatAud(wins)} centreLabel="Accenture Wins"
          slices={tier3} loading={summary.loading || offerings.loading}
        />
      </CardContent>
    </Card>
  );
}
