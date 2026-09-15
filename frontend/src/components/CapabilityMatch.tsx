import { useCallback, useMemo, useState } from "react";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Link,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RTooltip,
  Cell,
} from "recharts";
import { useApi } from "../api/useApi";
import { getScoredAtms, getAtmAiScore } from "../api/opportunities";
import type { ScoredAtmRow, AtmStatus, AiScoreResult } from "../api/opportunities";
import { formatDate } from "../lib/format";
import { competitorColor, ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, LABEL_SX, INK_MUTED, CARD_BORDER } from "../theme/dashboardStyles";

// ── color helpers ─────────────────────────────────────────────────────────────

const THREAT_COLOR: Record<string, string> = {
  high: "#DC2626",
  medium: "#D97706",
  low: "#16A34A",
};

const REC_COLOR: Record<string, { bg: string; fg: string }> = {
  pursue: { bg: "#DCFCE7", fg: "#166534" },
  watch: { bg: "#DBEAFE", fg: "#1E40AF" },
  monitor: { bg: "#FEF3C7", fg: "#92400E" },
  pass: { bg: "#F3F4F6", fg: "#6B7280" },
};

const GRADE_COLOR: Record<string, string> = {
  A: "#16A34A",
  B: "#0284C7",
  C: "#D97706",
  D: "#9CA3AF",
};

// urgency: 0 days → 100, 60+ days → 0
function urgency(days: number | null): number {
  if (days === null) return 0;
  return Math.max(0, Math.min(100, Math.round((1 - days / 60) * 100)));
}

// ── mini horizontal score bar ─────────────────────────────────────────────────

function ScoreBar({ value, color, height = 6 }: { value: number; color: string; height?: number }) {
  return (
    <Box sx={{ position: "relative", bgcolor: "#F1F3F5", borderRadius: 3, height, width: "100%", overflow: "hidden" }}>
      <Box sx={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${value}%`, bgcolor: color, borderRadius: 3 }} />
    </Box>
  );
}

// ── quadrant scatter ───────────────────────────────────────────────────────────

interface ScatterDatum {
  x: number;       // accenture score
  y: number;       // urgency
  z: number;       // bubble size (competitor pressure)
  atm: ScoredAtmRow;
}

function QuadrantScatter({
  data,
  selectedId,
  onSelect,
}: {
  data: ScatterDatum[];
  selectedId: string | null;
  onSelect: (atm: ScoredAtmRow) => void;
}) {
  return (
    <Box sx={{ ...CARD_SX, p: 2, position: "relative" }}>
      {/* Quadrant labels overlaid */}
      <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 1 }}>
        {[
          { label: "PURSUE NOW", top: "12%", right: "8%", color: "#166534" },
          { label: "MONITOR", top: "12%", left: "12%", color: "#92400E" },
          { label: "PLAN", bottom: "18%", right: "8%", color: "#1E40AF" },
          { label: "DEPRIORITISE", bottom: "18%", left: "12%", color: "#9CA3AF" },
        ].map((q) => (
          <Typography
            key={q.label}
            sx={{
              position: "absolute",
              top: q.top, bottom: q.bottom, left: q.left, right: q.right,
              fontSize: 10, fontWeight: 800, letterSpacing: ".1em",
              color: q.color, opacity: 0.35,
            }}
          >
            {q.label}
          </Typography>
        ))}
      </Box>

      <ResponsiveContainer width="100%" height={420}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 20 }}>
          {/* quadrant shading */}
          <ReferenceLine x={50} stroke={CARD_BORDER} strokeDasharray="4 4" />
          <ReferenceLine y={50} stroke={CARD_BORDER} strokeDasharray="4 4" />
          <XAxis
            type="number" dataKey="x" name="Accenture Fit" domain={[0, 100]}
            tick={{ fontSize: 11, fill: INK_MUTED }}
            label={{ value: "Accenture Capability Fit →", position: "insideBottom", offset: -20, fontSize: 12, fill: INK_MUTED }}
          />
          <YAxis
            type="number" dataKey="y" name="Urgency" domain={[0, 100]}
            tick={{ fontSize: 11, fill: INK_MUTED }}
            label={{ value: "Urgency →", angle: -90, position: "insideLeft", fontSize: 12, fill: INK_MUTED }}
          />
          <ZAxis type="number" dataKey="z" range={[60, 400]} />
          <RTooltip
            cursor={{ strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as ScatterDatum;
              return (
                <Box sx={{ ...CARD_SX, p: 1.5, maxWidth: 260 }}>
                  <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>{d.atm.title}</Typography>
                  <Typography sx={{ fontSize: 11, color: INK_MUTED }}>{d.atm.agency_name}</Typography>
                  <Divider sx={{ my: 0.75 }} />
                  <Typography sx={{ fontSize: 11 }}>Accenture fit: <b>{d.atm.accenture_score}</b> · {d.atm.days_to_close}d left</Typography>
                  <Typography sx={{ fontSize: 11 }}>Threat: <b style={{ color: THREAT_COLOR[d.atm.threat_level] }}>{d.atm.threat_level}</b></Typography>
                </Box>
              );
            }}
          />
          <Scatter data={data} onClick={(d) => onSelect((d as unknown as ScatterDatum).atm)} cursor="pointer">
            {data.map((d) => (
              <Cell
                key={d.atm.atm_id}
                fill={THREAT_COLOR[d.atm.threat_level]}
                fillOpacity={selectedId === d.atm.atm_id ? 1 : 0.7}
                stroke={selectedId === d.atm.atm_id ? ACCENTURE_COLOR : "#fff"}
                strokeWidth={selectedId === d.atm.atm_id ? 3 : 1}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </Box>
  );
}

// ── detail panel ────────────────────────────────────────────────────────────────

function DetailPanel({ atm }: { atm: ScoredAtmRow | null }) {
  const [ai, setAi] = useState<AiScoreResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const runAi = useCallback(async () => {
    if (!atm) return;
    setAiLoading(true);
    setAiError(null);
    setAi(null);
    try {
      const result = await getAtmAiScore(atm.atm_id);
      setAi(result);
    } catch (e) {
      setAiError(e instanceof Error ? e.message : "AI analysis failed");
    } finally {
      setAiLoading(false);
    }
  }, [atm]);

  if (!atm) {
    return (
      <Box sx={{ ...CARD_SX, p: 3, height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Typography sx={{ color: INK_MUTED, fontSize: 13, textAlign: "center" }}>
          Select an opportunity from the map or table<br />to see its capability breakdown.
        </Typography>
      </Box>
    );
  }

  const rec = REC_COLOR[atm.recommendation] ?? REC_COLOR.pass;
  const topCompetitors = atm.competitor_scores.slice(0, 6);

  return (
    <Box sx={{ ...CARD_SX, p: 2.5, height: "100%", overflow: "auto" }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
        <Typography sx={{ fontSize: 15, fontWeight: 700, lineHeight: 1.3 }}>{atm.title}</Typography>
        {atm.url && (
          <Link href={atm.url} target="_blank" rel="noopener noreferrer" sx={{ color: INK_MUTED, flexShrink: 0 }}>
            <OpenInNewIcon sx={{ fontSize: 16 }} />
          </Link>
        )}
      </Box>
      <Typography sx={{ fontSize: 12, color: INK_MUTED, mt: 0.5 }}>
        {atm.agency_name} · {atm.atm_type}
      </Typography>
      <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
        <Chip label={atm.recommendation.toUpperCase()} size="small" sx={{ fontSize: 10, fontWeight: 700, bgcolor: rec.bg, color: rec.fg }} />
        {atm.days_to_close !== null && (
          <Chip label={`${atm.days_to_close}d to close`} size="small" variant="outlined" sx={{ fontSize: 10, borderColor: CARD_BORDER, color: INK_MUTED }} />
        )}
        <Chip label={formatDate(atm.close_date)} size="small" variant="outlined" sx={{ fontSize: 10, borderColor: CARD_BORDER, color: INK_MUTED }} />
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Accenture score */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <Box sx={{ textAlign: "center" }}>
          <Typography sx={{ fontSize: 38, fontWeight: 800, lineHeight: 1, color: ACCENTURE_COLOR }}>
            {atm.accenture_score}
          </Typography>
          <Typography sx={{ fontSize: 10, color: INK_MUTED, letterSpacing: ".08em" }}>ACCENTURE FIT</Typography>
        </Box>
        <Chip
          label={`Grade ${atm.accenture_grade}`}
          size="small"
          sx={{ fontSize: 12, fontWeight: 800, bgcolor: `${GRADE_COLOR[atm.accenture_grade]}22`, color: GRADE_COLOR[atm.accenture_grade] }}
        />
      </Box>

      {/* Signal breakdown */}
      <Typography sx={{ ...LABEL_SX, mb: 1 }}>Signal breakdown</Typography>
      {[
        { label: "Track-record match (description ↔ past work)", value: Math.round(atm.accenture_capability_signal * 100) },
        { label: "UNSPSC category match", value: Math.round(atm.accenture_unspsc_signal * 100) },
      ].map((s) => (
        <Box key={s.label} sx={{ mb: 1.25 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
            <Typography sx={{ fontSize: 12, color: "#374151" }}>{s.label}</Typography>
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{s.value}</Typography>
          </Box>
          <ScoreBar value={s.value} color={ACCENTURE_COLOR} />
        </Box>
      ))}
      {/* Agency relationship: shown as a tick, deliberately not scored */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mt: 0.5 }}>
        <Typography sx={{ fontSize: 12, color: "#374151" }}>
          Prior relationship with {atm.agency_name?.split(" - ")[0] ?? "this agency"}
        </Typography>
        {atm.accenture_has_agency_relationship ? (
          <CheckCircleIcon sx={{ fontSize: 18, color: "#16A34A" }} />
        ) : (
          <RemoveCircleOutlineIcon sx={{ fontSize: 18, color: "#CBD5E1" }} />
        )}
      </Box>
      <Typography sx={{ fontSize: 10.5, color: INK_MUTED, mt: 0.5, fontStyle: "italic" }}>
        Not scored — informational only.
      </Typography>

      <Divider sx={{ my: 2 }} />

      {/* Competitor comparison */}
      <Box sx={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", mb: 1 }}>
        <Typography sx={LABEL_SX}>Competitor fit (who else can win)</Typography>
        <Typography sx={{ fontSize: 9.5, color: INK_MUTED }}>✓ = prior agency work</Typography>
      </Box>
      {topCompetitors.map((c) => (
        <Box key={c.slug} sx={{ mb: 1 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.25 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Typography sx={{ fontSize: 12, color: "#374151" }}>{c.label}</Typography>
              {c.has_agency_relationship && <CheckCircleIcon sx={{ fontSize: 13, color: "#16A34A" }} />}
            </Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{c.score}</Typography>
          </Box>
          <ScoreBar value={c.score} color={competitorColor(c.slug)} />
        </Box>
      ))}

      <Divider sx={{ my: 2 }} />

      {/* AI analysis */}
      <Button
        onClick={runAi}
        disabled={aiLoading}
        startIcon={aiLoading ? <CircularProgress size={14} sx={{ color: "#fff" }} /> : <AutoAwesomeIcon sx={{ fontSize: 16 }} />}
        variant="contained"
        fullWidth
        sx={{ bgcolor: ACCENTURE_COLOR, textTransform: "none", fontSize: 13, "&:hover": { bgcolor: "#8A00D6" } }}
      >
        {aiLoading ? "Analysing…" : ai ? "Re-run AI analysis" : "Analyse with AI"}
      </Button>

      {aiError && <Typography sx={{ fontSize: 12, color: "#DC2626", mt: 1 }}>{aiError}</Typography>}

      {ai && (
        <Box sx={{ mt: 2, p: 1.5, bgcolor: "#FAFAFF", borderRadius: 2, border: `1px solid ${CARD_BORDER}` }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <AutoAwesomeIcon sx={{ fontSize: 14, color: ACCENTURE_COLOR }} />
            <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: ".06em", color: ACCENTURE_COLOR }}>
              CLAUDE ANALYSIS · Fit {ai.accenture_score} ({ai.grade}) · {ai.recommendation.toUpperCase()}
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 12.5, color: "#1F2937", lineHeight: 1.5, mb: 1.5 }}>{ai.rationale}</Typography>

          {ai.win_factors.length > 0 && (
            <>
              <Typography sx={{ fontSize: 10.5, fontWeight: 700, color: "#166534", mb: 0.5 }}>WIN FACTORS</Typography>
              {ai.win_factors.map((f, i) => (
                <Typography key={i} sx={{ fontSize: 12, color: "#374151", mb: 0.3, pl: 1 }}>• {f}</Typography>
              ))}
            </>
          )}
          {ai.capability_gaps.length > 0 && (
            <>
              <Typography sx={{ fontSize: 10.5, fontWeight: 700, color: "#92400E", mt: 1, mb: 0.5 }}>CAPABILITY GAPS</Typography>
              {ai.capability_gaps.map((g, i) => (
                <Typography key={i} sx={{ fontSize: 12, color: "#374151", mb: 0.3, pl: 1 }}>• {g}</Typography>
              ))}
            </>
          )}
          {ai.competitor_threats.length > 0 && (
            <>
              <Typography sx={{ fontSize: 10.5, fontWeight: 700, color: "#B91C1C", mt: 1, mb: 0.5 }}>TOP THREATS</Typography>
              {ai.competitor_threats.map((t) => (
                <Box key={t.slug} sx={{ mb: 0.5, pl: 1 }}>
                  <Typography sx={{ fontSize: 12, color: "#374151" }}>
                    <b style={{ color: competitorColor(t.slug) }}>{t.label}</b> ({t.score}) — {t.reason}
                  </Typography>
                </Box>
              ))}
            </>
          )}
        </Box>
      )}
    </Box>
  );
}

// ── scored table ────────────────────────────────────────────────────────────────

function ScoredTable({
  rows,
  selectedId,
  onSelect,
}: {
  rows: ScoredAtmRow[];
  selectedId: string | null;
  onSelect: (atm: ScoredAtmRow) => void;
}) {
  return (
    <Box sx={{ ...CARD_SX, overflow: "hidden" }}>
      {/* header */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 90px 140px 200px 70px", gap: 1, px: 2, py: 1.25, bgcolor: "#F9FAFB", borderBottom: `1px solid ${CARD_BORDER}` }}>
        {["Opportunity", "Rec", "Accenture Fit", "Top Competitor Threats", "Closes"].map((h) => (
          <Typography key={h} sx={{ ...LABEL_SX, fontSize: 10.5 }}>{h}</Typography>
        ))}
      </Box>
      {rows.map((atm) => {
        const rec = REC_COLOR[atm.recommendation] ?? REC_COLOR.pass;
        const threats = atm.competitor_scores.slice(0, 3);
        return (
          <Box
            key={atm.atm_id}
            onClick={() => onSelect(atm)}
            sx={{
              display: "grid", gridTemplateColumns: "1fr 90px 140px 200px 70px", gap: 1, px: 2, py: 1.25,
              alignItems: "center", cursor: "pointer",
              borderBottom: `1px solid ${CARD_BORDER}`,
              bgcolor: selectedId === atm.atm_id ? "#FAF5FF" : "transparent",
              "&:hover": { bgcolor: "#F9FAFB" },
              "&:last-child": { borderBottom: 0 },
            }}
          >
            {/* opportunity */}
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {atm.title}
              </Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {atm.agency_name}
              </Typography>
            </Box>
            {/* rec */}
            <Chip label={atm.recommendation} size="small" sx={{ fontSize: 10, fontWeight: 700, bgcolor: rec.bg, color: rec.fg, textTransform: "capitalize" }} />
            {/* accenture fit */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box sx={{ flexGrow: 1 }}><ScoreBar value={atm.accenture_score} color={ACCENTURE_COLOR} height={8} /></Box>
              <Typography sx={{ fontSize: 13, fontWeight: 700, width: 24, textAlign: "right" }}>{atm.accenture_score}</Typography>
            </Box>
            {/* threats */}
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
              {threats.map((t) => (
                <Box key={t.slug} sx={{ display: "flex", alignItems: "center", gap: 0.5, bgcolor: "#F3F4F6", borderRadius: 1, px: 0.75, py: 0.25 }}>
                  <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: competitorColor(t.slug) }} />
                  <Typography sx={{ fontSize: 10.5, color: "#374151" }}>{t.label} {t.score}</Typography>
                </Box>
              ))}
            </Box>
            {/* closes */}
            <Typography sx={{ fontSize: 11.5, color: atm.days_to_close !== null && atm.days_to_close <= 7 ? "#B91C1C" : INK_MUTED, fontWeight: atm.days_to_close !== null && atm.days_to_close <= 7 ? 700 : 400 }}>
              {atm.days_to_close !== null ? `${atm.days_to_close}d` : "—"}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

// ── main ────────────────────────────────────────────────────────────────────────

export function CapabilityMatch({ statusFilter }: { statusFilter: AtmStatus }) {
  const [selected, setSelected] = useState<ScoredAtmRow | null>(null);

  const fetcher = useCallback(
    () => getScoredAtms({ defence_only: true, status: statusFilter, limit: 300 }),
    [statusFilter]
  );
  const { data, loading, error } = useApi(fetcher, [statusFilter]);

  const rows = data?.items ?? [];

  const scatterData: ScatterDatum[] = useMemo(
    () =>
      rows.map((atm) => ({
        x: atm.accenture_score,
        y: urgency(atm.days_to_close),
        z: 1 + atm.competitor_scores.filter((c) => c.score >= 45).length,
        atm,
      })),
    [rows]
  );

  // summary
  const pursue = rows.filter((r) => r.recommendation === "pursue").length;
  const highThreat = rows.filter((r) => r.threat_level === "high").length;
  const avgFit = rows.length ? Math.round(rows.reduce((s, r) => s + r.accenture_score, 0) / rows.length) : 0;

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress sx={{ color: ACCENTURE_COLOR }} />
      </Box>
    );
  }
  if (error) return <Typography sx={{ color: "#B91C1C", py: 4 }}>{error}</Typography>;

  return (
    <Box>
      {/* legend + summary */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Typography sx={{ fontSize: 13, color: INK_MUTED }}>
          <b style={{ color: "#111827" }}>{rows.length}</b> opportunities · <b style={{ color: "#166534" }}>{pursue}</b> to pursue · <b style={{ color: "#DC2626" }}>{highThreat}</b> high-threat · avg fit <b>{avgFit}</b>
        </Typography>
        <Chip
          label={data?.scoring_mode === "embedding" ? "Semantic embeddings" : "TF-IDF fallback (add embedding key)"}
          size="small"
          sx={{
            fontSize: 10, fontWeight: 700,
            bgcolor: data?.scoring_mode === "embedding" ? "#F3E8FF" : "#FEF3C7",
            color: data?.scoring_mode === "embedding" ? "#A100FF" : "#92400E",
          }}
        />
        <Box sx={{ display: "flex", gap: 1.5, ml: "auto" }}>
          {[["low", "Low threat"], ["medium", "Medium"], ["high", "High threat"]].map(([k, label]) => (
            <Box key={k} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: THREAT_COLOR[k] }} />
              <Typography sx={{ fontSize: 11, color: INK_MUTED }}>{label}</Typography>
            </Box>
          ))}
        </Box>
      </Box>

      {/* scatter + detail */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 2, mb: 2 }}>
        <QuadrantScatter data={scatterData} selectedId={selected?.atm_id ?? null} onSelect={setSelected} />
        <DetailPanel atm={selected} />
      </Box>

      {/* table */}
      <ScoredTable rows={rows} selectedId={selected?.atm_id ?? null} onSelect={setSelected} />
    </Box>
  );
}
