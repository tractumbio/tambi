import { useEffect, useState } from "react";
import { Box, Button, Card, CardContent, Chip, CircularProgress, Divider, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboard";
import RadarIcon from "@mui/icons-material/Radar";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import DescriptionIcon from "@mui/icons-material/Description";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import DownloadIcon from "@mui/icons-material/Download";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, CARD_BORDER } from "../theme/dashboardStyles";
import { getLatest, type MonthlyReportOut } from "../api/monthlyReports";
import { ReportView } from "../components/MonthlyReport";

const PURPLE = ACCENTURE_COLOR;

// ── architecture diagram ────────────────────────────────────────────────────────
function ArchitectureDiagram() {
  const box = (x: number, y: number, w: number, h: number, fill: string, stroke: string) => (
    <rect x={x} y={y} width={w} height={h} rx={10} fill={fill} stroke={stroke} strokeWidth={1.5} />
  );
  const arrow = (x1: number, y1: number, x2: number) => (
    <line x1={x1} y1={y1} x2={x2} y2={y1} stroke="#C4B5FD" strokeWidth={2} markerEnd="url(#ah)" />
  );
  return (
    <svg viewBox="0 0 980 300" style={{ width: "100%", height: "auto" }}>
      <defs>
        <marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
          <path d="M0,0 L9,4.5 L0,9 z" fill="#A78BFA" />
        </marker>
      </defs>

      {/* Column 1 — Sources */}
      <text x="105" y="24" textAnchor="middle" fontSize="11" fontWeight="700" fill={INK_MUTED} letterSpacing="1.5">SOURCES</text>
      {box(20, 40, 170, 60, "#F5F3FF", "#DDD6FE")}
      <text x="105" y="66" textAnchor="middle" fontSize="12.5" fontWeight="700" fill="#4C1D95">AusTender OCDS</text>
      <text x="105" y="84" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>awarded Defence contracts</text>
      {box(20, 120, 170, 60, "#F5F3FF", "#DDD6FE")}
      <text x="105" y="146" textAnchor="middle" fontSize="12.5" fontWeight="700" fill="#4C1D95">Reputable news</text>
      <text x="105" y="164" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>vetted outlet allowlist</text>

      {arrow(190, 70, 250)}
      {arrow(190, 150, 250)}

      {/* Column 2 — Stores */}
      <text x="335" y="24" textAnchor="middle" fontSize="11" fontWeight="700" fill={INK_MUTED} letterSpacing="1.5">WAREHOUSE</text>
      {box(255, 40, 160, 60, "#fff", CARD_BORDER)}
      <text x="335" y="66" textAnchor="middle" fontSize="12.5" fontWeight="700" fill="#111827">Contracts DB</text>
      <text x="335" y="84" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>Postgres · Defence-only</text>
      {box(255, 120, 160, 60, "#fff", CARD_BORDER)}
      <text x="335" y="146" textAnchor="middle" fontSize="12.5" fontWeight="700" fill="#111827">Knowledge base</text>
      <text x="335" y="164" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>accumulating · dedup'd</text>

      {arrow(415, 110, 475)}

      {/* Column 3 — Intelligence */}
      <text x="560" y="24" textAnchor="middle" fontSize="11" fontWeight="700" fill={INK_MUTED} letterSpacing="1.5">INTELLIGENCE</text>
      {box(480, 55, 160, 120, "#FAF5FF", "#E9D5FF")}
      <text x="560" y="88" textAnchor="middle" fontSize="12.5" fontWeight="700" fill={PURPLE}>Embeddings</text>
      <text x="560" y="106" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>capability match</text>
      <line x1="500" y1="120" x2="620" y2="120" stroke="#E9D5FF" strokeWidth="1" />
      <text x="560" y="140" textAnchor="middle" fontSize="12.5" fontWeight="700" fill={PURPLE}>LLM synthesis</text>
      <text x="560" y="158" textAnchor="middle" fontSize="10.5" fill={INK_MUTED}>numbers stay from SQL</text>

      {arrow(640, 115, 700)}

      {/* Column 4 — Products */}
      <text x="820" y="24" textAnchor="middle" fontSize="11" fontWeight="700" fill={INK_MUTED} letterSpacing="1.5">CAPABILITIES</text>
      {["Dashboard", "Opportunities", "Ask", "Research"].map((t, i) => (
        <g key={t}>
          {box(705, 40 + i * 55, 230, 44, "#fff", CARD_BORDER)}
          <circle cx="725" cy={62 + i * 55} r="4" fill={PURPLE} />
          <text x="740" y={66 + i * 55} fontSize="12.5" fontWeight="600" fill="#111827">{t}</text>
        </g>
      ))}
    </svg>
  );
}

// ── capability card ─────────────────────────────────────────────────────────────
interface Cap {
  tab: number;
  icon: React.ReactNode;
  title: string;
  tagline: string;
  points: string[];
}

function CapabilityCard({ cap, onNavigate }: { cap: Cap; onNavigate: (t: number) => void }) {
  return (
    <Card elevation={0} sx={{ ...CARD_SX, height: "100%", display: "flex", flexDirection: "column",
      transition: "all .15s", "&:hover": { borderColor: PURPLE, boxShadow: "0 4px 18px rgba(161,0,255,.08)" } }}>
      <CardContent sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1.5 }}>
          <Box sx={{ width: 40, height: 40, borderRadius: 2, bgcolor: "#F5F3FF", display: "flex",
            alignItems: "center", justifyContent: "center", color: PURPLE }}>{cap.icon}</Box>
          <Typography sx={{ fontSize: 17, fontWeight: 800 }}>{cap.title}</Typography>
        </Box>
        <Typography sx={{ fontSize: 13.5, color: "#374151", mb: 1.5, lineHeight: 1.55 }}>{cap.tagline}</Typography>
        <Box sx={{ flexGrow: 1 }}>
          {cap.points.map((p) => (
            <Box key={p} sx={{ display: "flex", gap: 1, mb: 0.75 }}>
              <Box sx={{ width: 5, height: 5, borderRadius: "50%", bgcolor: PURPLE, mt: "7px", flexShrink: 0 }} />
              <Typography sx={{ fontSize: 12.5, color: INK_MUTED, lineHeight: 1.5 }}>{p}</Typography>
            </Box>
          ))}
        </Box>
        <Button onClick={() => onNavigate(cap.tab)} endIcon={<ArrowForwardIcon />}
          sx={{ mt: 2, alignSelf: "flex-start", textTransform: "none", color: PURPLE, fontWeight: 600, px: 0,
            "&:hover": { bgcolor: "transparent", textDecoration: "underline" } }}>
          Open {cap.title}
        </Button>
      </CardContent>
    </Card>
  );
}

const CAPS: Cap[] = [
  {
    tab: 1, icon: <DashboardIcon />, title: "Dashboard",
    tagline: "Where Accenture stands in the addressable Defence services market.",
    points: ["Addressable market sizing & Accenture share", "Competitor positioning and momentum",
      "Service-offering breakdown and FY growth"],
  },
  {
    tab: 2, icon: <RadarIcon />, title: "Opportunities",
    tagline: "Live Approaches to Market, scored for capability fit.",
    points: ["Semantic match of each opportunity to real delivered work", "Fit vs every major competitor, side by side",
      "Pursue / watch quadrant and AI deep-dive"],
  },
  {
    tab: 3, icon: <QuestionAnswerIcon />, title: "Ask",
    tagline: "Question the contract warehouse in plain English.",
    points: ["Natural language → safe, read-only SQL", "Narrated answer with source contract ids",
      "Transparent — inspect the query and rows"],
  },
  {
    tab: 4, icon: <DescriptionIcon />, title: "Research & Reporting",
    tagline: "Standing monthly briefings plus ad-hoc investigations.",
    points: ["Contract movements, spend trends, market news", "Accumulating knowledge base with change-since-last-report",
      "Every number from SQL, every source cited"],
  },
];

// ── HTML export helper ──────────────────────────────────────────────────────────
function fmtAud(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function buildReportHtml(report: MonthlyReportOut): string {
  const p = report.payload;
  const spend = p.facts.spend;

  const movementRows = (items: typeof p.facts.new_awards.notable) =>
    items.slice(0, 6).map((n) =>
      `<tr><td>${n.title || n.cn_id || "—"}</td><td>${n.competitor_label}</td><td>${n.agency || "—"}</td><td style="text-align:right;font-weight:700">${fmtAud(n.value)}</td></tr>`
    ).join("");

  const newsItems = (cat: string) =>
    p.news.filter((n) => n.category === cat).map((n) => {
      const host = (() => { try { return new URL(n.url).hostname.replace("www.", ""); } catch { return n.url; } })();
      return `<div class="news-item"><div class="news-headline"><a href="${n.url}" target="_blank">${n.headline || "—"}</a>${n.is_new ? ' <span class="badge">NEW</span>' : ""}</div>${n.summary ? `<div class="news-summary">${n.summary}</div>` : ""}${n.relevance ? `<div class="relevance">${n.relevance}</div>` : ""}<div class="news-meta">${host}${n.published_date ? ` · ${n.published_date}` : ""}</div></div>`;
    }).join("");

  const momentum = p.facts.competitor_momentum.slice(0, 8).map((m) =>
    `<tr><td>${m.label}</td><td style="text-align:right;font-weight:700">${fmtAud(m.value_12m)}</td><td style="text-align:center">${m.trend === "up" ? "▲" : m.trend === "down" ? "▼" : "—"}</td></tr>`
  ).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
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
  .stat .num{font-size:22px;font-weight:800}
  .stat .lbl{font-size:11px;color:#9CA3AF}
  table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
  th{text-align:left;padding:6px 8px;background:#F9FAFB;border-bottom:2px solid #E5E7EB;font-size:11px;text-transform:uppercase;color:#6B7280}
  td{padding:6px 8px;border-bottom:1px solid #F3F4F6}
  tr:last-child td{border-bottom:none}
  .news-item{border:1px solid #E5E7EB;border-radius:6px;padding:10px 12px;margin-bottom:8px}
  .news-headline{font-weight:600;font-size:13px;margin-bottom:4px}
  .news-headline a{color:#111827;text-decoration:none}
  .news-headline a:hover{text-decoration:underline}
  .news-summary{font-size:12px;color:#4B5563;margin-bottom:3px}
  .relevance{font-size:11.5px;color:#A100FF;font-style:italic;margin-bottom:3px}
  .news-meta{font-size:10.5px;color:#9CA3AF}
  .badge{display:inline-block;padding:1px 6px;background:#DCFCE7;color:#166534;border-radius:4px;font-size:9px;font-weight:700;margin-left:6px;vertical-align:middle}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:600px){.grid2{grid-template-columns:1fr}.stats{gap:12px}}
  @media print{body{padding:16px}button{display:none}}
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

<div class="card">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#6B7280;margin-bottom:8px">Executive Summary</div>
  <p style="font-size:14.5px;color:#1F2937">${report.executive_summary || ""}</p>
</div>

<h2>1 · Contract Movements</h2>
<p>${p.narrative.contract_movements}</p>
<div class="grid2">
  <div>
    <h3 style="color:#166534">New Awards · ${fmtAud(p.facts.new_awards.total_value)} (${p.facts.new_awards.total_count})</h3>
    <table><thead><tr><th>Contract</th><th>Competitor</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.new_awards.notable)}</tbody></table>
  </div>
  <div>
    <h3 style="color:#92400E">Amendments · ${fmtAud(p.facts.amendments.total_value)} (${p.facts.amendments.total_count})</h3>
    <table><thead><tr><th>Contract</th><th>Competitor</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.amendments.notable)}</tbody></table>
  </div>
</div>
<h3 style="color:#B91C1C;margin-top:16px">Expiries &amp; Recompetes · ${fmtAud(p.facts.expiries.total_value)} (${p.facts.expiries.total_count})</h3>
<table><thead><tr><th>Contract</th><th>Incumbent</th><th>Agency</th><th style="text-align:right">Value</th></tr></thead><tbody>${movementRows(p.facts.expiries.notable)}</tbody></table>

<h2>2 · Expenditure &amp; Market Trends</h2>
<p>${p.narrative.expenditure_trends}</p>
<div class="stats">
  <div class="stat"><div class="num">${fmtAud(spend.new_award_value)}</div><div class="lbl">new-award value${spend.delta_pct != null ? ` · ${spend.delta_pct >= 0 ? "+" : ""}${spend.delta_pct}%` : ""}</div></div>
  <div class="stat"><div class="num" style="color:#A100FF">${fmtAud(spend.accenture_value)}</div><div class="lbl">Accenture · ${(spend.accenture_share * 100).toFixed(1)}% share</div></div>
</div>
<h3>Competitor Momentum (rolling 12m)</h3>
<table style="max-width:500px"><thead><tr><th>Competitor</th><th style="text-align:right">Value</th><th style="text-align:center">Trend</th></tr></thead><tbody>${momentum}</tbody></table>

<h2>3 · Market Intelligence</h2>
<p>${p.narrative.market_news}</p>
${["competitor", "government", "macro"].map((cat) => {
  const items = newsItems(cat);
  return items ? `<h3>${cat}</h3>${items}` : "";
}).join("")}

<div class="card accent" style="margin-top:24px">
  <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#A100FF;margin-bottom:8px">Implications &amp; Watch-list for Accenture</div>
  <p style="font-size:14.5px;color:#1F2937">${p.narrative.implications}</p>
</div>
</body>
</html>`;
}

export function LandingPage({ onNavigate }: { onNavigate: (tab: number) => void }) {
  const [report, setReport] = useState<MonthlyReportOut | null>(null);
  const [reportLoading, setReportLoading] = useState(true);

  useEffect(() => {
    getLatest()
      .then(setReport)
      .catch(() => {})
      .finally(() => setReportLoading(false));
  }, []);

  const saveAsHtml = () => {
    if (!report) return;
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
    if (!report) return;
    const html = buildReportHtml(report);
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 400);
  };

  return (
    <Box>
      {/* Hero */}
      <Box sx={{ mb: 4 }}>
        <Chip label="ACCENTURE ANZ · DEFENCE" size="small"
          sx={{ bgcolor: "#F5F3FF", color: PURPLE, fontWeight: 700, fontSize: 10.5, letterSpacing: ".08em", mb: 1.5 }} />
        <Typography sx={{ fontSize: 34, fontWeight: 800, letterSpacing: "-.02em", lineHeight: 1.1, mb: 1 }}>
          Defence Contract Intelligence,<br />end to end.
        </Typography>
        <Typography sx={{ fontSize: 16, color: INK_MUTED, maxWidth: "72ch", lineHeight: 1.6 }}>
          TAMBI turns five years of AusTender awards and a curated news stream into a single decision surface —
          market position, live opportunities, natural-language analysis, and automated monthly reporting.
          Figures are computed deterministically from the warehouse; AI narrates and matches, but never invents the numbers.
        </Typography>
      </Box>

      {/* Architecture diagram */}
      <Card elevation={0} sx={{ ...CARD_SX, mb: 4 }}>
        <CardContent>
          <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: INK_MUTED, mb: 2 }}>
            How it works
          </Typography>
          <ArchitectureDiagram />
        </CardContent>
      </Card>

      {/* Capability cards */}
      <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: INK_MUTED, mb: 2 }}>
        The four capabilities
      </Typography>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 2.5 }}>
        {CAPS.map((c) => <CapabilityCard key={c.tab} cap={c} onNavigate={onNavigate} />)}
      </Box>

      {/* Latest monthly report */}
      {(reportLoading || report) && (
        <Box sx={{ mt: 6 }}>
          <Divider sx={{ mb: 4 }} />
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3, flexWrap: "wrap", gap: 1.5 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: INK_MUTED }}>
              Latest Monthly Report
            </Typography>
            {report && (
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button size="small" variant="outlined" startIcon={<DownloadIcon />} onClick={saveAsHtml}
                  sx={{ textTransform: "none", fontSize: 12.5, borderColor: "#D1D5DB", color: "#374151",
                    "&:hover": { borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR } }}>
                  Save as HTML
                </Button>
                <Button size="small" variant="outlined" startIcon={<PictureAsPdfIcon />} onClick={saveAsPdf}
                  sx={{ textTransform: "none", fontSize: 12.5, borderColor: "#D1D5DB", color: "#374151",
                    "&:hover": { borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR } }}>
                  Save as PDF
                </Button>
              </Box>
            )}
          </Box>
          {reportLoading && <CircularProgress size={24} sx={{ color: ACCENTURE_COLOR }} />}
          {report && <ReportView report={report} />}
        </Box>
      )}
    </Box>
  );
}
