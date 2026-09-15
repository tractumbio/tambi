import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Box, Card, CardContent, Chip, Skeleton, Typography } from "@mui/material";
import { getPeerComparison } from "../api/metrics";
import { useApi } from "../api/useApi";
import { formatAud, formatPct } from "../lib/format";
import { ACCENTURE_COLOR, competitorColor } from "../theme/competitorColors";
import { CARD_SX, INK, INK_MUTED, LABEL_SX, tooltipStyle } from "../theme/dashboardStyles";
import type { CommonFilterParams, PeerCohort } from "../types";

const GRID = "#E7ECF3";
const SLATE = "#526070";
const COHORT_GREY = "#9AA4B2";

const COHORTS: { cohort: PeerCohort; heading: string }[] = [
  { cohort: "big4", heading: "Accenture vs Big 4" },
  { cohort: "mbb", heading: "Accenture vs MBB" },
  { cohort: "challengers", heading: "Accenture vs Challengers" },
];

export function CompetitivePosition({ filter }: { filter?: CommonFilterParams }) {
  return (
    <Box sx={{ mt: 4 }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>
          Competitive position
        </Typography>
        <Typography variant="h6">Accenture vs Peer Cohorts</Typography>
        <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: .5 }}>
          Head-to-head on the Accenture-addressable Defence services market.
        </Typography>
      </Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {COHORTS.map((c) => (
          <PeerPanel key={c.cohort} cohort={c.cohort} heading={c.heading} filter={filter} />
        ))}
      </Box>
    </Box>
  );
}

function PeerPanel({ cohort, heading, filter }: {
  cohort: PeerCohort; heading: string; filter?: CommonFilterParams;
}) {
  const { data, loading } = useApi(
    () => getPeerComparison(cohort, true, filter),
    [cohort, filter?.theme ?? "all"],
  );

  return (
    <Card elevation={0} sx={CARD_SX}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
          <Typography sx={{ fontSize: 15, fontWeight: 700, color: INK }}>{heading}</Typography>
          <Chip label={data?.cohort_label ?? "…"} size="small" variant="outlined"
            sx={{ fontSize: 11, color: INK_MUTED, borderColor: "#e5e7eb" }} />
        </Box>

        {loading ? <Skeleton variant="rectangular" height={200} /> : !data ? null : (
          <Box sx={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr 1.2fr", gap: 3, alignItems: "center" }}>
            {/* Headline + share bar */}
            <Box>
              <Typography sx={LABEL_SX}>Accenture share of pair</Typography>
              <Typography sx={{ fontSize: 34, fontWeight: 800, color: ACCENTURE_COLOR, letterSpacing: "-.03em", lineHeight: 1.1 }}>
                {formatPct(data.accenture_share)}
              </Typography>
              <Box sx={{ display: "flex", height: 10, borderRadius: 5, overflow: "hidden", my: 1.25 }}>
                <Box sx={{ width: `${data.accenture_share * 100}%`, bgcolor: ACCENTURE_COLOR }} />
                <Box sx={{ flexGrow: 1, bgcolor: COHORT_GREY }} />
              </Box>
              <Row swatch={ACCENTURE_COLOR} label="Accenture" value={data.accenture_value} n={data.accenture_count} />
              <Row swatch={COHORT_GREY} label={data.cohort_label} value={data.cohort_value} n={data.cohort_count} />
            </Box>

            {/* Accenture vs each cohort firm */}
            <Box>
              <Typography sx={{ ...LABEL_SX, mb: 1 }}>Accenture vs cohort firms</Typography>
              {(() => {
                const bars = [
                  { slug: "accenture", label: "Accenture", value: data.accenture_value, contract_count: data.accenture_count },
                  ...data.members,
                ];
                return (
                  <ResponsiveContainer width="100%" height={Math.max(120, bars.length * 34)}>
                    <BarChart layout="vertical" data={bars} margin={{ left: 8, right: 12 }}>
                      <CartesianGrid strokeDasharray="2 4" stroke={GRID} horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} />
                      <YAxis type="category" dataKey="label" width={92} tick={{ fontSize: 11, fill: INK }} />
                      <Tooltip formatter={(v: number) => [formatAud(v), "Value"]} contentStyle={tooltipStyle} />
                      <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                        {bars.map((m) => (
                          <Cell key={m.slug} fill={competitorColor(m.slug)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                );
              })()}
            </Box>

            {/* FY trend: one line per firm (Accenture + each cohort member) */}
            <Box>
              <Typography sx={{ ...LABEL_SX, mb: 1 }}>By financial year · per firm</Typography>
              {data.series.length === 0 ? (
                <Typography sx={{ fontSize: 13, color: "#98A2B3", py: 3 }}>No history.</Typography>
              ) : (() => {
                const firms = [
                  { slug: "accenture", label: "Accenture" },
                  ...data.members.map((m) => ({ slug: m.slug, label: m.label })),
                ];
                const chartData = data.series.map((p) => ({ fy_label: p.fy_label, ...p.firms }));
                return (
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={chartData} margin={{ top: 4, right: 8, left: 8 }}>
                      <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
                      <XAxis dataKey="fy_label" tick={{ fontSize: 11, fill: SLATE }} />
                      <YAxis tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => formatAud(v as number)} width={48} />
                      <Tooltip formatter={(v: number, n: string) => [formatAud(v), firmLabel(firms, n)]}
                        contentStyle={tooltipStyle} />
                      {firms.map((fm) => (
                        <Line
                          key={fm.slug} type="monotone" dataKey={fm.slug} name={fm.label}
                          stroke={competitorColor(fm.slug)} dot={false}
                          strokeWidth={fm.slug === "accenture" ? 2.75 : 1.5}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                );
              })()}
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function firmLabel(firms: { slug: string; label: string }[], slug: string): string {
  return firms.find((f) => f.slug === slug)?.label ?? slug;
}

function Row({ swatch, label, value, n }: { swatch: string; label: string; value: number; n: number }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: .75 }}>
      <Box sx={{ width: 9, height: 9, borderRadius: "2px", bgcolor: swatch, flexShrink: 0 }} />
      <Typography sx={{ fontSize: 13, color: INK, flexGrow: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {label}
      </Typography>
      <Typography sx={{ fontSize: 13, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{formatAud(value)}</Typography>
      <Typography sx={{ fontSize: 12, color: INK_MUTED, minWidth: 34, textAlign: "right" }}>{n}</Typography>
    </Box>
  );
}
