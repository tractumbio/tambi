import { useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, Collapse,
  IconButton, InputBase, Link, Typography,
} from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import SlideshowIcon from "@mui/icons-material/Slideshow";
import CodeIcon from "@mui/icons-material/Code";
import EditIcon from "@mui/icons-material/Edit";
import { generateVisual, type VisualizeResponse } from "../api/visualize";
import { formatAud } from "../lib/format";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, tooltipStyle } from "../theme/dashboardStyles";

const GRID = "#E7ECF3";
const SLATE = "#526070";

const EXAMPLES = [
  "Bar chart of top 10 competitors by total contract value",
  "Line chart: Accenture contract value by financial year",
  "Competitor value by defence theme — grouped bar",
  "Top 8 agencies by number of contracts awarded",
];

// ── dynamic chart renderer ────────────────────────────────────────────────────
function DynamicChart({ spec }: { spec: VisualizeResponse }) {
  const { chart_type, x_key, series, data } = spec;
  const fmt = (v: unknown) => typeof v === "number" ? (v > 1e4 ? formatAud(v) : String(v)) : String(v ?? "");

  if (chart_type === "pie" && series.length > 0) {
    const pieData = data.map((d) => ({ name: String(d[x_key] ?? ""), value: Number(d[series[0].key]) || 0 }));
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} label={(e) => e.name}>
            {pieData.map((_, i) => <Cell key={i} fill={series[i % series.length]?.color ?? ACCENTURE_COLOR} />)}
          </Pie>
          <Tooltip formatter={(v: number) => [fmt(v), ""]} contentStyle={tooltipStyle} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chart_type === "horizontal_bar") {
    return (
      <ResponsiveContainer width="100%" height={Math.max(220, data.length * 30)}>
        <BarChart layout="vertical" data={data} margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="2 4" stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => fmt(v)} />
          <YAxis type="category" dataKey={x_key} width={140} tick={{ fontSize: 10, fill: "#374151" }} />
          <Tooltip formatter={(v, n) => [fmt(v), series.find((s) => s.key === n)?.label ?? String(n)]} contentStyle={tooltipStyle} />
          {series.length > 1 && <Legend />}
          {series.map((s) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[0, 3, 3, 0]} />)}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chart_type === "line") {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 4, right: 12, left: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
          <XAxis dataKey={x_key} tick={{ fontSize: 11, fill: SLATE }} />
          <YAxis tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => fmt(v)} width={56} />
          <Tooltip formatter={(v, n) => [fmt(v), series.find((s) => s.key === n)?.label ?? String(n)]} contentStyle={tooltipStyle} />
          {series.length > 1 && <Legend />}
          {series.map((s, i) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label}
              stroke={s.color} strokeWidth={i === 0 ? 2.5 : 1.8} dot={data.length < 20} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chart_type === "area") {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 8 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={s.color} stopOpacity={0.18} />
                <stop offset="95%" stopColor={s.color} stopOpacity={0.01} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
          <XAxis dataKey={x_key} tick={{ fontSize: 11, fill: SLATE }} />
          <YAxis tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => fmt(v)} width={56} />
          <Tooltip formatter={(v, n) => [fmt(v), series.find((s) => s.key === n)?.label ?? String(n)]} contentStyle={tooltipStyle} />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Area key={s.key} type="monotone" dataKey={s.key} name={s.label}
              stroke={s.color} strokeWidth={2} fill={`url(#grad-${s.key})`} dot={false} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  // default: bar
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 12, left: 8 }}>
        <CartesianGrid strokeDasharray="2 4" stroke={GRID} vertical={false} />
        <XAxis dataKey={x_key} tick={{ fontSize: 11, fill: SLATE }} />
        <YAxis tick={{ fontSize: 11, fill: SLATE }} tickFormatter={(v) => fmt(v)} width={56} />
        <Tooltip formatter={(v, n) => [fmt(v), series.find((s) => s.key === n)?.label ?? String(n)]} contentStyle={tooltipStyle} />
        {series.length > 1 && <Legend />}
        {series.map((s) => <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[3, 3, 0, 0]} />)}
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── PDF export ────────────────────────────────────────────────────────────────
function buildVisualHtml(spec: VisualizeResponse): string {
  const tableRows = spec.data.slice(0, 50).map((r) =>
    `<tr>${spec.series.map((s) => `<td style="text-align:right;padding:4px 8px">${r[s.key] ?? "—"}</td>`).join("")}<td style="padding:4px 8px">${r[spec.x_key] ?? ""}</td></tr>`
  ).join("");
  const thCols = [...spec.series.map((s) => `<th style="padding:6px 8px;background:#F9FAFB;font-size:11px">${s.label}</th>`), `<th style="padding:6px 8px;background:#F9FAFB;font-size:11px">${spec.x_key}</th>`].join("");
  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><title>${spec.title}</title>
<style>body{font-family:-apple-system,sans-serif;padding:32px;max-width:900px;margin:0 auto}h1{font-size:22px;font-weight:800;margin-bottom:4px}p{color:#6B7280;font-size:13px;margin-bottom:20px}table{width:100%;border-collapse:collapse;font-size:12.5px}th{text-align:left;border-bottom:2px solid #E5E7EB}td{border-bottom:1px solid #F3F4F6}@media print{body{padding:16px}}</style>
</head><body>
<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#A100FF;margin-bottom:4px">TAMBI · Visual Studio</div>
<h1>${spec.title}</h1>
<p>${spec.insight}</p>
<p style="font-size:11px;color:#9CA3AF">SQL: ${spec.sql}</p>
<table><thead><tr>${thCols}</tr></thead><tbody>${tableRows}</tbody></table>
</body></html>`;
}

function exportPdf(spec: VisualizeResponse) {
  const html = buildVisualHtml(spec);
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => { win.print(); }, 400);
}

async function exportPpt(spec: VisualizeResponse) {
  const { default: PptxGenJS } = await import("pptxgenjs");
  const prs = new PptxGenJS();
  prs.layout = "LAYOUT_WIDE";

  const slide = prs.addSlide();
  slide.background = { color: "FFFFFF" };
  slide.addText("TAMBI · Visual Studio", { x: 0.5, y: 0.25, w: 12, h: 0.3, fontSize: 9, bold: true, color: "A100FF", charSpacing: 2 });
  slide.addText(spec.title, { x: 0.5, y: 0.55, w: 12, h: 0.55, fontSize: 22, bold: true, color: "111827" });
  slide.addText(spec.insight, { x: 0.5, y: 1.15, w: 12, h: 0.45, fontSize: 11, color: "6B7280" });

  const chartData = spec.series.map((s) => ({
    name: s.label,
    labels: spec.data.map((d) => String(d[spec.x_key] ?? "")),
    values: spec.data.map((d) => Number(d[s.key]) || 0),
  }));

  const pptType = spec.chart_type === "line" || spec.chart_type === "area"
    ? prs.ChartType.line
    : spec.chart_type === "pie" ? prs.ChartType.pie : prs.ChartType.bar;

  slide.addChart(pptType as Parameters<typeof slide.addChart>[0], chartData, {
    x: 0.5, y: 1.7, w: 12, h: 4.2,
    chartColors: spec.series.map((s) => s.color.replace("#", "").toUpperCase()),
    showLegend: spec.series.length > 1,
    legendPos: "b",
    showTitle: false,
    valAxisLabelFontSize: 10,
    catAxisLabelFontSize: 10,
  } as Parameters<typeof slide.addChart>[2]);

  const dataSlide = prs.addSlide();
  dataSlide.addText("Data", { x: 0.5, y: 0.3, w: 12, h: 0.4, fontSize: 16, bold: true, color: "111827" });
  const rows = [
    [spec.x_key, ...spec.series.map((s) => s.label)].map((h) => ({ text: h, options: { bold: true, fontSize: 10 } })),
    ...spec.data.slice(0, 30).map((d) => [
      { text: String(d[spec.x_key] ?? ""), options: { fontSize: 9 } },
      ...spec.series.map((s) => ({ text: String(d[s.key] ?? ""), options: { fontSize: 9 } })),
    ]),
  ];
  dataSlide.addTable(rows as Parameters<typeof dataSlide.addTable>[0], { x: 0.5, y: 0.8, w: 12, colW: 2, fontSize: 9 });

  await prs.writeFile({ fileName: `tambi-visual-${Date.now()}.pptx` });
}

// ── main component ────────────────────────────────────────────────────────────
export function VisualStudio() {
  const [input, setInput] = useState("");
  const [refineInput, setRefineInput] = useState("");
  const [spec, setSpec] = useState<VisualizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [showRefine, setShowRefine] = useState(false);
  const [exporting, setExporting] = useState<"pdf" | "ppt" | null>(null);

  const generate = async (prompt: string, refine?: string) => {
    const q = prompt.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await generateVisual(q, refine || undefined, refine && spec ? spec as unknown as object : undefined);
      setSpec(result);
      setShowRefine(false);
      setRefineInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!spec) return;
    setExporting("pdf");
    try { exportPdf(spec); } finally { setExporting(null); }
  };

  const handleExportPpt = async () => {
    if (!spec) return;
    setExporting("ppt");
    try { await exportPpt(spec); } finally { setExporting(null); }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Visual Studio</Typography>
        <Typography variant="h6" sx={{ fontWeight: 800, fontSize: 17 }}>Generate a Visual</Typography>
        <Typography sx={{ fontSize: 12.5, color: INK_MUTED, mt: 0.25 }}>
          Describe any chart — Claude writes the query, fetches the data, and renders it.
        </Typography>
      </Box>

      {/* Input */}
      <Card elevation={0} sx={{ border: `1.5px solid ${ACCENTURE_COLOR}`, mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", px: 1.5, py: 0.75 }}>
          <InputBase
            fullWidth placeholder="Describe the chart you want…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && generate(input)}
            disabled={loading}
            sx={{ fontSize: 14 }}
          />
          <IconButton onClick={() => generate(input)} disabled={!input.trim() || loading} sx={{ color: ACCENTURE_COLOR }}>
            {loading ? <CircularProgress size={18} sx={{ color: ACCENTURE_COLOR }} /> : <ArrowForwardIcon />}
          </IconButton>
        </Box>
      </Card>

      {/* Examples */}
      {!spec && !loading && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mb: 2 }}>
          {EXAMPLES.map((q) => (
            <Box key={q} onClick={() => { setInput(q); generate(q); }}
              sx={{ px: 1.5, py: 1, border: "1px solid #E4E4E4", borderRadius: 1, cursor: "pointer", fontSize: 13, color: "#3C3C3C",
                "&:hover": { borderColor: ACCENTURE_COLOR, color: ACCENTURE_COLOR, bgcolor: "rgba(161,0,255,.03)" }, transition: "all .15s" }}>
              {q}
            </Box>
          ))}
        </Box>
      )}

      {/* Error */}
      {error && <Typography sx={{ fontSize: 13, color: "#B91C1C", mb: 1.5 }}>{error}</Typography>}

      {/* Chart output */}
      {spec && (
        <Card elevation={0} sx={{ ...CARD_SX, flexGrow: 1 }}>
          <CardContent>
            {/* Chart header */}
            <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 1.5, gap: 1 }}>
              <Box>
                <Typography sx={{ fontSize: 15, fontWeight: 700 }}>{spec.title}</Typography>
                <Typography sx={{ fontSize: 12.5, color: INK_MUTED, mt: 0.3 }}>{spec.insight}</Typography>
              </Box>
              <Box sx={{ display: "flex", gap: 0.75, flexShrink: 0, flexWrap: "wrap" }}>
                <Chip size="small" label={spec.chart_type.replace("_", " ")} sx={{ fontSize: 10 }} />
              </Box>
            </Box>

            {/* Chart */}
            <DynamicChart spec={spec} />

            {/* Actions */}
            <Box sx={{ display: "flex", gap: 1, mt: 2, flexWrap: "wrap", alignItems: "center" }}>
              <Button size="small" variant="outlined" startIcon={<EditIcon sx={{ fontSize: 14 }} />}
                onClick={() => setShowRefine((v) => !v)}
                sx={{ textTransform: "none", fontSize: 12, borderColor: "#D1D5DB", color: "#374151" }}>
                Refine with AI
              </Button>
              <Button size="small" variant="outlined" startIcon={exporting === "pdf" ? <CircularProgress size={12} /> : <PictureAsPdfIcon sx={{ fontSize: 14 }} />}
                onClick={handleExportPdf} disabled={exporting !== null}
                sx={{ textTransform: "none", fontSize: 12, borderColor: "#D1D5DB", color: "#374151" }}>
                Save as PDF
              </Button>
              <Button size="small" variant="outlined" startIcon={exporting === "ppt" ? <CircularProgress size={12} /> : <SlideshowIcon sx={{ fontSize: 14 }} />}
                onClick={handleExportPpt} disabled={exporting !== null}
                sx={{ textTransform: "none", fontSize: 12, borderColor: "#D1D5DB", color: "#374151" }}>
                Save as PPT
              </Button>
              <Link component="button" onClick={() => setShowSql((v) => !v)}
                sx={{ fontSize: 11.5, color: INK_MUTED, display: "inline-flex", alignItems: "center", gap: 0.5, textDecoration: "none", ml: "auto" }}>
                <CodeIcon sx={{ fontSize: 14 }} /> {showSql ? "Hide" : "View"} SQL
              </Link>
            </Box>

            {/* Refine input */}
            <Collapse in={showRefine}>
              <Box sx={{ mt: 2, display: "flex", gap: 1, alignItems: "center" }}>
                <InputBase fullWidth placeholder="E.g. 'make it a line chart', 'add KPMG', 'sort descending'…"
                  value={refineInput} onChange={(e) => setRefineInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && generate(input, refineInput)}
                  sx={{ fontSize: 13, border: "1px solid #E5E7EB", borderRadius: 1, px: 1.5, py: 0.75 }} />
                <Button size="small" variant="contained" startIcon={loading ? <CircularProgress size={12} sx={{ color: "#fff" }} /> : <AutoFixHighIcon />}
                  disabled={!refineInput.trim() || loading}
                  onClick={() => generate(input, refineInput)}
                  sx={{ textTransform: "none", fontSize: 12.5, bgcolor: ACCENTURE_COLOR, "&:hover": { bgcolor: "#8a00d8" }, flexShrink: 0 }}>
                  Apply
                </Button>
              </Box>
            </Collapse>

            {/* SQL disclosure */}
            <Collapse in={showSql}>
              <Box sx={{ mt: 1.5, p: 1.5, bgcolor: "#0B1220", borderRadius: 1, overflow: "auto" }}>
                <Typography component="pre" sx={{ fontFamily: "monospace", fontSize: 11, color: "#A5D6FF", whiteSpace: "pre-wrap", m: 0 }}>
                  {spec.sql}
                </Typography>
              </Box>
            </Collapse>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
