import { useCallback, useEffect, useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogContent,
  DialogTitle, IconButton, LinearProgress, Link, MenuItem, Select, TextField, Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import SourceIcon from "@mui/icons-material/Source";
import AddIcon from "@mui/icons-material/Add";
import CloudSyncIcon from "@mui/icons-material/CloudSync";
import {
  generateReport, getDefaultStructure, getReport, listReports, getCoverage,
  listDomains, addDomain, removeDomain, triggerHarvest,
  type MonthlyReportOut, type MonthlyReportSummary, type MovementItem, type MovementSection, type NewsDomain,
  type Coverage,
} from "../api/monthlyReports";
import { formatAud, formatDate } from "../lib/format";
import { InfoTooltip } from "./InfoTooltip";
import { ACCENTURE_COLOR, competitorColor } from "../theme/competitorColors";
import { CARD_SX, LABEL_SX, INK_MUTED, CARD_BORDER } from "../theme/dashboardStyles";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";

const MODELS = [
  { id: "claude-sonnet-5", label: "Sonnet 5 · balanced" },
  { id: "claude-opus-5", label: "Opus 5 · deepest" },
  { id: "claude-haiku-4-5-20251001", label: "Haiku · fastest" },
];
const EFFORTS = [{ id: "low", label: "Low" }, { id: "standard", label: "Standard" }, { id: "deep", label: "Deep" }];

interface SourcesInfo { data_sources: string[]; news_domains: string[]; corpus_size: number; }

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}
function last30(): { start: string; end: string } {
  const end = new Date();
  end.setDate(end.getDate() + 1);
  const start = new Date(end);
  start.setDate(start.getDate() - 30);
  return { start: iso(start), end: iso(end) };
}

function Label({ children, mt = 3 }: { children: React.ReactNode; mt?: number }) {
  return <Typography sx={{ ...LABEL_SX, mb: 1, mt }}>{children}</Typography>;
}

// ── contract detail dialog ───────────────────────────────────────────────────
function ContractDialog({ item, onClose }: { item: MovementItem; onClose: () => void }) {
  const dur = item.date_published && item.period_end
    ? Math.round((new Date(item.period_end).getTime() - new Date(item.date_published).getTime()) / (1000 * 60 * 60 * 24 * 30))
    : null;
  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", pr: 1 }}>
        <Box sx={{ pr: 2 }}>
          <Typography sx={{ fontSize: 10, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: ACCENTURE_COLOR, mb: 0.5 }}>
            Contract Detail
          </Typography>
          <Typography sx={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35 }}>
            {item.title || item.cn_id || "Unnamed contract"}
          </Typography>
        </Box>
        <IconButton size="small" onClick={onClose} sx={{ mt: -0.5, flexShrink: 0 }}><CloseIcon sx={{ fontSize: 18 }} /></IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 0 }}>
        {[
          ["Agency", item.agency],
          ["Supplier / Firm", item.supplier],
          ["Competitor group", item.competitor_label],
          ["CN ID", item.cn_id],
          ["Value", item.value != null ? formatAud(item.value) : null],
          ["Start", item.date_published ? formatDate(item.date_published) : null],
          ["Expiry", item.period_end ? formatDate(item.period_end) : null],
          ["Duration", dur != null ? `${dur} months` : null],
        ].filter(([, v]) => v).map(([label, value]) => (
          <Box key={label as string} sx={{ display: "flex", gap: 2, py: 0.75, borderBottom: "1px solid #F3F4F6" }}>
            <Typography sx={{ fontSize: 12, color: INK_MUTED, width: 130, flexShrink: 0 }}>{label}</Typography>
            <Typography sx={{ fontSize: 13, fontWeight: 500 }}>{value}</Typography>
          </Box>
        ))}
      </DialogContent>
    </Dialog>
  );
}

// ── movement table (new awards / amendments / expiries) ─────────────────────────
function MovementTable({ section, kind }: { section: MovementSection; kind: string }) {
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [openContract, setOpenContract] = useState<MovementItem | null>(null);

  if (!section || section.total_count === 0) {
    return <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>No {kind} in this period.</Typography>;
  }
  const named = section.by_competitor.filter((c) => c.slug !== "other").slice(0, 6);
  const visible = selectedSlug
    ? section.notable.filter((n) => n.competitor_slug === selectedSlug)
    : section.notable.slice(0, 6);

  return (
    <Box sx={{ mt: 1 }}>
      <Box sx={{ display: "flex", gap: 3, mb: 1.5, flexWrap: "wrap" }}>
        <Box><Typography sx={{ fontSize: 22, fontWeight: 800, color: "#111827" }}>{section.total_count}</Typography>
          <Typography sx={{ fontSize: 11, color: INK_MUTED }}>{kind}</Typography></Box>
        <Box><Typography sx={{ fontSize: 22, fontWeight: 800, color: "#111827" }}>{formatAud(section.total_value)}</Typography>
          <Typography sx={{ fontSize: 11, color: INK_MUTED }}>total value</Typography></Box>
      </Box>
      {named.length > 0 && (
        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", mb: 1.5 }}>
          {named.map((c) => (
            <Chip
              key={c.slug}
              size="small"
              label={`${c.label} · ${formatAud(c.value)} (${c.count})`}
              onClick={() => setSelectedSlug((prev) => prev === c.slug ? null : c.slug)}
              sx={{
                fontSize: 11, cursor: "pointer",
                bgcolor: selectedSlug === c.slug ? `${competitorColor(c.slug)}30` : `${competitorColor(c.slug)}18`,
                color: "#374151",
                borderLeft: `3px solid ${competitorColor(c.slug)}`,
                borderRadius: "4px",
                outline: selectedSlug === c.slug ? `2px solid ${competitorColor(c.slug)}` : "none",
                "&:hover": { bgcolor: `${competitorColor(c.slug)}28` },
              }}
            />
          ))}
        </Box>
      )}
      {selectedSlug && (
        <Typography sx={{ fontSize: 11, color: INK_MUTED, mb: 0.75 }}>
          Showing {visible.length} contract{visible.length !== 1 ? "s" : ""} for {named.find((c) => c.slug === selectedSlug)?.label ?? selectedSlug} — <Box component="span" onClick={() => setSelectedSlug(null)} sx={{ cursor: "pointer", color: ACCENTURE_COLOR }}>clear filter</Box>
        </Typography>
      )}
      <Box sx={{ ...CARD_SX, overflow: "hidden" }}>
        {visible.length === 0 ? (
          <Typography sx={{ fontSize: 13, color: INK_MUTED, px: 1.5, py: 1 }}>No notable contracts for this firm.</Typography>
        ) : visible.map((n, i) => (
          <Box
            key={i}
            onClick={() => setOpenContract(n)}
            sx={{
              display: "flex", justifyContent: "space-between", gap: 2, px: 1.5, py: 1,
              borderBottom: i < visible.length - 1 ? `1px solid ${CARD_BORDER}` : 0,
              alignItems: "center", cursor: "pointer",
              "&:hover": { bgcolor: "#FAF5FF" }, transition: "background .12s",
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography sx={{ fontSize: 12.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {n.title || n.cn_id || "—"}
              </Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED }}>
                {n.competitor_label}{n.agency ? ` · ${n.agency}` : ""}{n.cn_id ? ` · ${n.cn_id}` : ""}
              </Typography>
            </Box>
            <Typography sx={{ fontSize: 13, fontWeight: 700, flexShrink: 0 }}>{formatAud(n.value)}</Typography>
          </Box>
        ))}
      </Box>
      {openContract && <ContractDialog item={openContract} onClose={() => setOpenContract(null)} />}
    </Box>
  );
}

// ── HTML export builder ──────────────────────────────────────────────────────────
function buildReportHtml(report: MonthlyReportOut): string {
  const p = report.payload;
  const spend = p.facts.spend;
  const fa = formatAud;

  const movementRows = (items: typeof p.facts.new_awards.notable) =>
    items.slice(0, 6).map((n) =>
      `<tr><td>${n.title || n.cn_id || "—"}</td><td>${n.competitor_label}</td><td>${n.agency || "—"}</td><td style="text-align:right;font-weight:700">${fa(n.value ?? 0)}</td></tr>`
    ).join("");

  const newsItems = (cat: string) =>
    p.news.filter((n) => n.category === cat).map((n) => {
      const host = (() => { try { return new URL(n.url).hostname.replace("www.", ""); } catch { return n.url; } })();
      return `<div class="news-item"><div class="news-headline"><a href="${n.url}" target="_blank">${n.headline || "—"}</a>${n.is_new ? ' <span class="badge">NEW</span>' : ""}</div>${n.summary ? `<div class="news-summary">${n.summary}</div>` : ""}${n.relevance ? `<div class="relevance">${n.relevance}</div>` : ""}<div class="news-meta">${host}${n.published_date ? ` · ${n.published_date}` : ""}</div></div>`;
    }).join("");

  const momentum = p.facts.competitor_momentum.slice(0, 8).map((m) =>
    `<tr><td>${m.label}</td><td style="text-align:right;font-weight:700">${fa(m.value_12m)}</td><td style="text-align:center">${m.trend === "up" ? "▲" : m.trend === "down" ? "▼" : "—"}</td></tr>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>${report.title || "TAMBI Monthly Report"}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;color:#111827;background:#fff;padding:32px;max-width:900px;margin:0 auto}
  h1{font-size:26px;font-weight:800;margin-bottom:4px}
  h2{font-size:16px;font-weight:700;margin:28px 0 8px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280}
  h3{font-size:13px;font-weight:700;margin:16px 0 6px;text-transform:uppercase;color:#9CA3AF}
  p{line-height:1.7;margin-bottom:8px;color:#374151}
  .label{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#A100FF;margin-bottom:4px}
  .meta{font-size:12px;color:#9CA3AF;margin-bottom:24px}
  .card{border:1px solid #E5E7EB;border-radius:8px;padding:16px;margin-bottom:16px}
  .card.purple{background:#FAF5FF;border-color:#E9D5FF}
  .card.accent{border-color:#A100FF;background:rgba(161,0,255,.03)}
  .stats{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:12px}
  .stat .num{font-size:22px;font-weight:800}.stat .lbl{font-size:11px;color:#9CA3AF}
  table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
  th{text-align:left;padding:6px 8px;background:#F9FAFB;border-bottom:2px solid #E5E7EB;font-size:11px;text-transform:uppercase;color:#6B7280}
  td{padding:6px 8px;border-bottom:1px solid #F3F4F6}
  tr:last-child td{border-bottom:none}
  .news-item{border:1px solid #E5E7EB;border-radius:6px;padding:10px 12px;margin-bottom:8px}
  .news-headline{font-weight:600;font-size:13px;margin-bottom:4px}
  .news-headline a{color:#111827;text-decoration:none}.news-headline a:hover{text-decoration:underline}
  .news-summary{font-size:12px;color:#4B5563;margin-bottom:3px}
  .relevance{font-size:11.5px;color:#A100FF;font-style:italic;margin-bottom:3px}
  .news-meta{font-size:10.5px;color:#9CA3AF}
  .badge{display:inline-block;padding:1px 6px;background:#DCFCE7;color:#166534;border-radius:4px;font-size:9px;font-weight:700;margin-left:6px;vertical-align:middle}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:600px){.grid2{grid-template-columns:1fr}.stats{gap:12px}}
  @media print{body{padding:16px}}
</style>
</head>
<body>
<div class="label">TAMBI · Market Intelligence Report</div>
<h1>${report.title || "Monthly Market Intelligence"}</h1>
<div class="meta">Generated ${new Date(report.generated_at).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" })} · ${report.contract_source_count} contract sources · ${report.news_source_count} news items · ${report.model?.replace("claude-", "").replace("-20251001", "") || ""} · ${report.effort || ""}</div>

<div class="card purple">
  <div class="stats">
    <div class="stat"><div class="num">${p.knowledge_change.new_items}</div><div class="lbl">new intelligence items</div></div>
    <div class="stat"><div class="num">${p.knowledge_change.delta_pct == null ? "—" : `${p.knowledge_change.delta_pct >= 0 ? "+" : ""}${p.knowledge_change.delta_pct}%`}</div><div class="lbl">vs prior period</div></div>
    <div class="stat"><div class="num">${p.knowledge_change.total_corpus}</div><div class="lbl">total knowledge base</div></div>
  </div>
</div>
<div class="card"><div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#6B7280;margin-bottom:8px">Executive Summary</div>
<p style="font-size:14.5px;color:#1F2937">${report.executive_summary || ""}</p></div>

<h2>1 · Contract Movements</h2>
<p>${p.narrative.contract_movements}</p>
<div class="grid2">
  <div><h3 style="color:#166534">New Awards · ${fa(p.facts.new_awards.total_value)} (${p.facts.new_awards.total_count})</h3>
  <table><thead><tr><th>Contract</th><th>Competitor</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.new_awards.notable)}</tbody></table></div>
  <div><h3 style="color:#92400E">Amendments · ${fa(p.facts.amendments.total_value)} (${p.facts.amendments.total_count})</h3>
  <table><thead><tr><th>Contract</th><th>Competitor</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.amendments.notable)}</tbody></table></div>
</div>
<h3 style="color:#B91C1C;margin-top:16px">Expiries &amp; Recompetes · ${fa(p.facts.expiries.total_value)} (${p.facts.expiries.total_count})</h3>
<table><thead><tr><th>Contract</th><th>Incumbent</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.expiries.notable)}</tbody></table>

<h2>2 · Expenditure &amp; Market Trends</h2>
<p>${p.narrative.expenditure_trends}</p>
<div class="stats">
  <div class="stat"><div class="num">${fa(spend.new_award_value)}</div><div class="lbl">new-award value${spend.delta_pct != null ? ` · ${spend.delta_pct >= 0 ? "+" : ""}${spend.delta_pct}%` : ""}</div></div>
  <div class="stat"><div class="num" style="color:#A100FF">${fa(spend.accenture_value)}</div><div class="lbl">Accenture · ${(spend.accenture_share * 100).toFixed(1)}% share</div></div>
</div>
<h3>Competitor Momentum (rolling 12m)</h3>
<table style="max-width:500px"><thead><tr><th>Competitor</th><th style="text-align:right">Value</th><th style="text-align:center">Trend</th></tr></thead><tbody>${momentum}</tbody></table>

<h2>3 · Market Intelligence</h2>
<p>${p.narrative.market_news}</p>
${["competitor", "government", "macro"].map((cat) => { const items = newsItems(cat); return items ? `<h3>${cat}</h3>${items}` : ""; }).join("")}

<div class="card accent" style="margin-top:24px">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#A100FF;margin-bottom:8px">Implications &amp; Watch-list for Accenture</div>
  <p style="font-size:14.5px;color:#1F2937">${p.narrative.implications}</p>
</div>
</body></html>`;
}

// ── report viewer ────────────────────────────────────────────────────────────────
export function ReportView({ report }: { report: MonthlyReportOut }) {
  const p = report.payload;
  const kc = p.knowledge_change;
  const spend = p.facts.spend;
  const newsByCat = (cat: string) => p.news.filter((n) => n.category === cat);
  const deltaColor = kc.delta_pct == null ? INK_MUTED : kc.delta_pct >= 0 ? "#166534" : "#B91C1C";

  const saveAsHtml = () => {
    const html = buildReportHtml(report);
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tambi-report-${report.period_start}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const saveAsPdf = () => {
    const html = buildReportHtml(report);
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 400);
  };

  return (
    <Card elevation={0} sx={{ ...CARD_SX, overflow: "hidden", maxWidth: 960 }}>
      {/* Download toolbar */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2,
        px: 2.5, py: 1.5, borderBottom: `1px solid ${CARD_BORDER}`, bgcolor: "#FAFAFA", flexWrap: "wrap" }}>
        <Box>
          <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: ACCENTURE_COLOR, fontWeight: 700 }}>
            Market Intelligence Report
          </Typography>
          <Typography sx={{ fontSize: 15, fontWeight: 800, lineHeight: 1.3 }}>{report.title}</Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
          {report.model && <Chip size="small" label={report.model.replace("claude-", "").replace("-20251001", "")} sx={{ fontSize: 10 }} />}
          {report.effort && <Chip size="small" label={report.effort} variant="outlined" sx={{ fontSize: 10 }} />}
          <Button size="small" variant="outlined" startIcon={<DownloadIcon />} onClick={saveAsHtml}
            sx={{ textTransform: "none", fontSize: 12, borderColor: "#D1D5DB", color: "#374151",
              "&:hover": { borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR } }}>
            HTML
          </Button>
          <Button size="small" variant="outlined" startIcon={<PictureAsPdfIcon />} onClick={saveAsPdf}
            sx={{ textTransform: "none", fontSize: 12, borderColor: "#D1D5DB", color: "#374151",
              "&:hover": { borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR } }}>
            PDF
          </Button>
        </Box>
      </Box>

      <Box sx={{ p: 3 }}>
      <Typography sx={{ fontSize: 12, color: INK_MUTED, mb: 2 }}>
        Generated {formatDate(report.generated_at)} · {report.contract_source_count} contract sources · {report.news_source_count} news items
      </Typography>

      {/* Change-since-last banner */}
      <Card elevation={0} sx={{ ...CARD_SX, mb: 2, bgcolor: "#FAF5FF", borderColor: "#E9D5FF" }}>
        <CardContent sx={{ "&:last-child": { pb: 2 } }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 3, flexWrap: "wrap" }}>
            <Box>
              <Typography sx={{ fontSize: 26, fontWeight: 800, color: ACCENTURE_COLOR }}>{kc.new_items}</Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED }}>new intelligence items</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 20, fontWeight: 700, color: deltaColor }}>
                {kc.delta_pct == null ? "—" : `${kc.delta_pct >= 0 ? "+" : ""}${kc.delta_pct}%`}
              </Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED }}>vs prior period ({kc.prev_window_items})</Typography>
            </Box>
            <Box>
              <Typography sx={{ fontSize: 20, fontWeight: 700 }}>{kc.total_corpus}</Typography>
              <Typography sx={{ fontSize: 11, color: INK_MUTED }}>total knowledge base</Typography>
            </Box>
            {kc.top_entities.length > 0 && (
              <Box sx={{ ml: "auto" }}>
                <Typography sx={{ fontSize: 10, color: INK_MUTED, mb: 0.5 }}>MOST COVERED</Typography>
                <Box sx={{ display: "flex", gap: 0.5 }}>
                  {kc.top_entities.slice(0, 4).map((e) => (
                    <Chip key={e.slug} size="small" label={`${e.slug} ${e.count}`}
                      sx={{ fontSize: 10, bgcolor: `${competitorColor(e.slug)}22` }} />
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Executive summary */}
      <Card elevation={0} sx={{ ...CARD_SX, mb: 1 }}>
        <CardContent>
          <Typography sx={{ ...LABEL_SX, mb: 1 }}>Executive Summary</Typography>
          <Typography sx={{ fontSize: 14.5, lineHeight: 1.7, color: "#1F2937" }}>{report.executive_summary}</Typography>
        </CardContent>
      </Card>

      {/* Section 1 — Contract Movements */}
      <Box sx={{ display: "flex", alignItems: "center", mt: 3, mb: 1 }}>
        <Typography sx={{ ...LABEL_SX }}>1 · Contract Movements</Typography>
        <InfoTooltip text="Computed deterministically from AusTender: new awards are contracts with date_published in the selected window; amendments detected via amendment_count > 0; expiries are contracts with period_end in the window." />
      </Box>
      <Typography sx={{ fontSize: 14, lineHeight: 1.7, color: "#374151", mb: 1 }}>{p.narrative.contract_movements}</Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2, mt: 1 }}>
        <Box><Typography sx={{ fontSize: 12, fontWeight: 700, color: "#166534" }}>New awards</Typography>
          <MovementTable section={p.facts.new_awards} kind="new awards" /></Box>
        <Box><Typography sx={{ fontSize: 12, fontWeight: 700, color: "#92400E" }}>Amendments</Typography>
          <MovementTable section={p.facts.amendments} kind="amendments" /></Box>
      </Box>
      <Box sx={{ mt: 2 }}>
        <Typography sx={{ fontSize: 12, fontWeight: 700, color: "#B91C1C" }}>Expiries & recompetes</Typography>
        <MovementTable section={p.facts.expiries} kind="expiries" />
      </Box>

      {/* Section 2 — Expenditure & Trends */}
      <Box sx={{ display: "flex", alignItems: "center", mt: 3, mb: 1 }}>
        <Typography sx={{ ...LABEL_SX }}>2 · Expenditure & Market Trends</Typography>
        <InfoTooltip text="Total award value from the SQL warehouse for the period. Accenture share = Accenture value ÷ total. Competitor momentum uses a rolling 12-month window with trend direction vs prior 12 months." />
      </Box>
      <Typography sx={{ fontSize: 14, lineHeight: 1.7, color: "#374151", mb: 1.5 }}>{p.narrative.expenditure_trends}</Typography>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 1.5 }}>
        <Box sx={{ ...CARD_SX, p: 1.5, minWidth: 150 }}>
          <Typography sx={{ fontSize: 20, fontWeight: 800 }}>{formatAud(spend.new_award_value)}</Typography>
          <Typography sx={{ fontSize: 11, color: INK_MUTED }}>new-award value ·
            <span style={{ color: (spend.delta_pct ?? 0) >= 0 ? "#166534" : "#B91C1C", fontWeight: 700 }}>
              {" "}{spend.delta_pct == null ? "—" : `${spend.delta_pct >= 0 ? "+" : ""}${spend.delta_pct}%`}</span></Typography>
        </Box>
        <Box sx={{ ...CARD_SX, p: 1.5, minWidth: 150 }}>
          <Typography sx={{ fontSize: 20, fontWeight: 800, color: ACCENTURE_COLOR }}>{formatAud(spend.accenture_value)}</Typography>
          <Typography sx={{ fontSize: 11, color: INK_MUTED }}>Accenture share {(spend.accenture_share * 100).toFixed(1)}%</Typography>
        </Box>
      </Box>
      <Label mt={1}>Competitor momentum (rolling 12m)</Label>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
        {p.facts.competitor_momentum.slice(0, 6).map((m) => (
          <Box key={m.slug} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: competitorColor(m.slug) }} />
            <Typography sx={{ fontSize: 12.5, width: 150 }}>{m.label}</Typography>
            <Typography sx={{ fontSize: 12.5, fontWeight: 700, width: 80 }}>{formatAud(m.value_12m)}</Typography>
            {m.trend === "up" ? <TrendingUpIcon sx={{ fontSize: 16, color: "#16A34A" }} />
              : m.trend === "down" ? <TrendingDownIcon sx={{ fontSize: 16, color: "#DC2626" }} />
              : <Box sx={{ width: 16, height: 2, bgcolor: INK_MUTED }} />}
          </Box>
        ))}
      </Box>

      {/* Section 3 — Market Intelligence */}
      <Box sx={{ display: "flex", alignItems: "center", mt: 3, mb: 1 }}>
        <Typography sx={{ ...LABEL_SX }}>3 · Market Intelligence</Typography>
        <InfoTooltip text="Live web searches run by Claude at report-generation time, scoped to major competitors, Defence policy, and macro-economic themes. Each item carries a source URL; relevance assessed by the model." />
      </Box>
      <Typography sx={{ fontSize: 14, lineHeight: 1.7, color: "#374151", mb: 1.5 }}>{p.narrative.market_news}</Typography>
      {(["competitor", "government", "macro"] as const).map((cat) => {
        const items = newsByCat(cat);
        if (items.length === 0) return null;
        return (
          <Box key={cat} sx={{ mb: 1.5 }}>
            <Typography sx={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: INK_MUTED, mb: 0.75 }}>{cat}</Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {items.map((n, i) => (
                <Box key={i} sx={{ ...CARD_SX, p: 1.25 }}>
                  <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 600, lineHeight: 1.35 }}>
                      {n.headline}
                      {n.is_new && <Chip label="NEW" size="small" sx={{ ml: 1, height: 16, fontSize: 9, fontWeight: 700, bgcolor: "#DCFCE7", color: "#166534" }} />}
                    </Typography>
                    <Link href={n.url} target="_blank" rel="noopener noreferrer" sx={{ color: INK_MUTED, flexShrink: 0 }}>
                      <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </Link>
                  </Box>
                  {n.summary && <Typography sx={{ fontSize: 12, color: "#4B5563", mt: 0.3 }}>{n.summary}</Typography>}
                  {n.relevance && <Typography sx={{ fontSize: 11.5, color: ACCENTURE_COLOR, mt: 0.4, fontStyle: "italic" }}>{n.relevance}</Typography>}
                  <Typography sx={{ fontSize: 10.5, color: INK_MUTED, mt: 0.4 }}>
                    {(() => { try { return new URL(n.url).hostname.replace("www.", ""); } catch { return n.url; } })()}
                    {n.published_date ? ` · ${n.published_date}` : ""}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Box>
        );
      })}

      {/* Implications */}
      <Card elevation={0} sx={{ ...CARD_SX, mt: 2, borderColor: ACCENTURE_COLOR, bgcolor: "rgba(161,0,255,.03)" }}>
        <CardContent>
          <Typography sx={{ ...LABEL_SX, mb: 1, color: ACCENTURE_COLOR }}>Implications & Watch-list for Accenture</Typography>
          <Typography sx={{ fontSize: 14.5, lineHeight: 1.7, color: "#1F2937" }}>{p.narrative.implications}</Typography>
        </CardContent>
      </Card>
      </Box>
    </Card>
  );
}

// ── editable reputable-domains manager ──────────────────────────────────────────
function DomainsPanel({ dataSources, corpusSize }: { dataSources: string[]; corpusSize: number }) {
  const [domains, setDomains] = useState<NewsDomain[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = useCallback(() => { listDomains().then(setDomains).catch(() => {}); }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const add = async () => {
    const d = input.trim();
    if (!d) return;
    setBusy(true); setMsg(null);
    try { await addDomain(d); setInput(""); refresh(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Failed to add"); }
    finally { setBusy(false); }
  };
  const remove = async (d: string) => { await removeDomain(d).then(refresh).catch(() => {}); };
  const harvest = async () => {
    setBusy(true); setMsg(null);
    try { const r = await triggerHarvest(); setMsg(`Harvested ${r.inserted} new · ${r.updated} seen`); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Harvest failed"); }
    finally { setBusy(false); }
  };

  return (
    <Card elevation={0} sx={{ ...CARD_SX, mt: 2 }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1 }}>
          <SourceIcon sx={{ fontSize: 16, color: INK_MUTED }} />
          <Typography sx={LABEL_SX}>Sources feeding the report</Typography>
        </Box>
        <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#374151", mb: 0.5 }}>Contract warehouse (deterministic)</Typography>
        {dataSources.map((s) => (
          <Typography key={s} sx={{ fontSize: 11.5, color: INK_MUTED, mb: 0.25 }}>• {s}</Typography>
        ))}

        <Typography sx={{ fontSize: 11, fontWeight: 700, color: "#374151", mt: 1.5, mb: 0.75 }}>
          Reputable news outlets · {corpusSize} items collected
        </Typography>
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: 1 }}>
          {domains.map((d) => (
            <Chip key={d.domain} label={d.domain} size="small" onDelete={() => remove(d.domain)}
              sx={{ fontSize: 10, height: 22, bgcolor: "#F5F3FF", color: "#4C1D95",
                "& .MuiChip-deleteIcon": { fontSize: 14, color: "#A78BFA" } }} />
          ))}
        </Box>
        <Box sx={{ display: "flex", gap: 0.75 }}>
          <TextField size="small" fullWidth placeholder="add domain, e.g. defensenews.com" value={input}
            onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()}
            sx={{ "& input": { fontSize: 11.5, py: 0.75 } }} />
          <Button size="small" onClick={add} disabled={busy || !input.trim()} variant="outlined"
            sx={{ minWidth: 36, borderColor: CARD_BORDER, color: ACCENTURE_COLOR }}><AddIcon sx={{ fontSize: 16 }} /></Button>
        </Box>
        <Button size="small" onClick={harvest} disabled={busy} startIcon={busy ? <CircularProgress size={12} /> : <CloudSyncIcon sx={{ fontSize: 15 }} />}
          sx={{ mt: 1, textTransform: "none", fontSize: 12, color: ACCENTURE_COLOR }}>
          Harvest news now
        </Button>
        {msg && <Typography sx={{ fontSize: 11, color: INK_MUTED, mt: 0.5 }}>{msg}</Typography>}
      </CardContent>
    </Card>
  );
}

// ── data-coverage summary for the selected period ──────────────────────────────
function CoveragePanel({ c }: { c: Coverage }) {
  const row = (label: string, value: string, sub?: string) => (
    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", py: 0.4 }}>
      <Typography sx={{ fontSize: 12, color: "#374151" }}>{label}</Typography>
      <Typography sx={{ fontSize: 12.5, fontWeight: 700 }}>{value}{sub && <span style={{ color: INK_MUTED, fontWeight: 400 }}> {sub}</span>}</Typography>
    </Box>
  );
  const grp = (title: string, children: React.ReactNode) => (
    <Box sx={{ mb: 1 }}>
      <Typography sx={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: ACCENTURE_COLOR, mb: 0.3 }}>{title}</Typography>
      {children}
    </Box>
  );
  return (
    <Card elevation={0} sx={{ ...CARD_SX, mt: 2 }}>
      <CardContent>
        <Typography sx={{ ...LABEL_SX, mb: 1 }}>In this period · {c.period.days} days</Typography>
        {grp("Contract breakdowns", <>
          {row("New awards", String(c.contracts.new_awards), formatAud(c.contracts.new_value))}
          {row("Amendments", String(c.contracts.amendments))}
          {row("Expiries / recompetes", String(c.contracts.expiries), formatAud(c.contracts.expiry_value))}
        </>)}
        {grp("Opportunities", <>
          {row("Open ATMs", String(c.opportunities.open_atms))}
          {row("Closing in period", String(c.opportunities.closing_in_period))}
        </>)}
        {grp("Relevant media", <>
          {row("Total items", String(c.media.total))}
          {Object.entries(c.media.by_category).map(([k, v]) => row(`· ${k}`, String(v)))}
        </>)}
        {grp("Defence releases", row("Government items", String(c.defence_releases)))}
      </CardContent>
    </Card>
  );
}

// ── main ──────────────────────────────────────────────────────────────────────
export function MonthlyReport() {
  const initial = last30();
  const [start, setStart] = useState(initial.start);
  const [end, setEnd] = useState(initial.end);
  const [model, setModel] = useState(MODELS[0].id);
  const [effort, setEffort] = useState("standard");
  const [structure, setStructure] = useState("");
  const [sources, setSources] = useState<SourcesInfo | null>(null);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [reports, setReports] = useState<MonthlyReportSummary[]>([]);
  const [selected, setSelected] = useState<MonthlyReportOut | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openReport = useCallback((id: number) => {
    getReport(id).then(setSelected).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    getDefaultStructure().then((r) => setStructure(r.structure)).catch(() => {});
    fetch(`${API_BASE_URL}/monthly-reports/sources`).then((r) => r.json()).then(setSources).catch(() => {});
    listReports().then((rs) => {
      setReports(rs);
      if (rs.length > 0) openReport(rs[0].id);
    }).catch(() => {});
  }, [openReport]);

  // Refresh the data-coverage summary whenever the period changes.
  useEffect(() => {
    if (start && end && end > start) getCoverage(start, end).then(setCoverage).catch(() => setCoverage(null));
  }, [start, end]);

  const run = useCallback(async () => {
    setRunning(true); setError(null); setSelected(null);
    try {
      const r = await generateReport({ period_start: start, period_end: end, model, effort, structure });
      setSelected(r);
      setReports(await listReports());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setRunning(false);
    }
  }, [start, end, model, effort, structure]);

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 3, alignItems: "start" }}>
      {/* Left rail — controls + sources + history */}
      <Box>
        <Card elevation={0} sx={{ ...CARD_SX }}>
          <CardContent>
            <Typography sx={{ ...LABEL_SX, mb: 1.5 }}>Generate a report</Typography>
            <Typography sx={{ fontSize: 11, color: INK_MUTED, mb: 0.5 }}>Period (defaults to last 30 days)</Typography>
            <Box sx={{ display: "flex", gap: 1, mb: 1.5 }}>
              <TextField type="date" size="small" fullWidth value={start} onChange={(e) => setStart(e.target.value)}
                label="From" InputLabelProps={{ shrink: true }} sx={{ "& input": { fontSize: 12 } }} />
              <TextField type="date" size="small" fullWidth value={end} onChange={(e) => setEnd(e.target.value)}
                label="To" InputLabelProps={{ shrink: true }} sx={{ "& input": { fontSize: 12 } }} />
            </Box>
            <Box sx={{ display: "flex", gap: 1, mb: 1.5 }}>
              <Box sx={{ flex: 1 }}>
                <Typography sx={{ fontSize: 11, color: INK_MUTED, mb: 0.5 }}>Model</Typography>
                <Select size="small" fullWidth value={model} onChange={(e) => setModel(e.target.value)} sx={{ fontSize: 12 }}>
                  {MODELS.map((m) => <MenuItem key={m.id} value={m.id} sx={{ fontSize: 12 }}>{m.label}</MenuItem>)}
                </Select>
              </Box>
              <Box sx={{ width: 110 }}>
                <Typography sx={{ fontSize: 11, color: INK_MUTED, mb: 0.5 }}>Effort</Typography>
                <Select size="small" fullWidth value={effort} onChange={(e) => setEffort(e.target.value)} sx={{ fontSize: 12 }}>
                  {EFFORTS.map((x) => <MenuItem key={x.id} value={x.id} sx={{ fontSize: 12 }}>{x.label}</MenuItem>)}
                </Select>
              </Box>
            </Box>
            <Typography sx={{ fontSize: 11, color: INK_MUTED, mb: 0.5 }}>Report structure (editable)</Typography>
            <TextField multiline minRows={6} maxRows={12} size="small" fullWidth value={structure}
              onChange={(e) => setStructure(e.target.value)}
              sx={{ mb: 1.5, "& textarea": { fontSize: 11.5, lineHeight: 1.5, fontFamily: "inherit" } }} />
            <Button variant="contained" fullWidth disableElevation onClick={run} disabled={running}
              startIcon={running ? <CircularProgress size={14} sx={{ color: "#fff" }} /> : <AutoAwesomeIcon />}
              sx={{ bgcolor: ACCENTURE_COLOR, "&:hover": { bgcolor: "#7500C0" }, textTransform: "none", fontWeight: 600 }}>
              {running ? "Generating…" : "Generate report"}
            </Button>
            {running && <LinearProgress sx={{ mt: 1, borderRadius: 1, "& .MuiLinearProgress-bar": { bgcolor: ACCENTURE_COLOR }, bgcolor: "#EADCFA" }} />}
            {error && <Typography sx={{ fontSize: 12, color: "#C62828", mt: 1 }}>{error}</Typography>}
          </CardContent>
        </Card>

        {/* Data-coverage summary for the selected period */}
        {coverage && <CoveragePanel c={coverage} />}

        {/* Sources + editable domain allowlist */}
        {sources && <DomainsPanel dataSources={sources.data_sources} corpusSize={sources.corpus_size} />}

        {/* History */}
        {reports.length > 0 && (
          <Card elevation={0} sx={{ ...CARD_SX, mt: 2 }}>
            <CardContent>
              <Typography sx={{ ...LABEL_SX, mb: 1 }}>Past reports</Typography>
              {reports.map((r) => (
                <Box key={r.id} onClick={() => openReport(r.id)}
                  sx={{ py: 0.75, px: 1, borderRadius: 1, cursor: "pointer", "&:hover": { bgcolor: "#F9FAFB" },
                    bgcolor: selected?.id === r.id ? "#FAF5FF" : "transparent" }}>
                  <Typography sx={{ fontSize: 12.5, fontWeight: 600 }}>{r.title}</Typography>
                  <Typography sx={{ fontSize: 11, color: INK_MUTED }}>
                    {formatDate(r.generated_at)} · {r.news_source_count} news · {r.model?.replace("claude-", "").replace("-20251001", "")}
                  </Typography>
                </Box>
              ))}
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Right — report viewer or empty state */}
      <Box>
        {running ? (
          <Card elevation={0} sx={{ ...CARD_SX, bgcolor: "#FAF5FF" }}>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1 }}>
                <CircularProgress size={18} sx={{ color: ACCENTURE_COLOR }} />
                <Typography sx={{ fontWeight: 700 }}>Compiling the briefing…</Typography>
              </Box>
              <Typography sx={{ fontSize: 13.5, color: INK_MUTED, lineHeight: 1.6 }}>
                Computing contract movements from the warehouse, reading the knowledge base, and synthesising the report.
              </Typography>
            </CardContent>
          </Card>
        ) : selected ? (
          <ReportView report={selected} />
        ) : (
          <Card elevation={0} sx={{ ...CARD_SX, p: 4, textAlign: "center" }}>
            <Typography sx={{ color: INK_MUTED, fontSize: 14 }}>
              Configure a period, model and structure, then <b>Generate report</b> —<br />
              or open a past report from the left.
            </Typography>
          </Card>
        )}
      </Box>
    </Box>
  );
}
