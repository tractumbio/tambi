import { useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  InputBase, LinearProgress, TextareaAutosize, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import SearchIcon from "@mui/icons-material/Search";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import { commissionResearch, ResearchReport } from "../api/research";
import { MonthlyReport } from "../components/MonthlyReport";
import { INK_MUTED } from "../theme/dashboardStyles";

const EXAMPLE_BRIEF =
  "Assess the competitive landscape for defence ICT sustainment and identify where Accenture is structurally disadvantaged relative to incumbents.";

export function ResearchPage() {
  const [view, setView] = useState<"report" | "brief">("report");
  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>Research &amp; Reporting</Typography>
        <Typography sx={{ color: INK_MUTED, mt: 0.5, maxWidth: "78ch", fontSize: 15 }}>
          Standing monthly market-intelligence reports, plus ad-hoc investigations — every figure drawn
          from the contract warehouse and every source cited.
        </Typography>
      </Box>
      <ToggleButtonGroup size="small" exclusive value={view} onChange={(_, v) => v && setView(v)}
        sx={{ mb: 3, "& .MuiToggleButton-root": { fontSize: 13, px: 2, textTransform: "none", color: INK_MUTED, gap: 0.75 },
          "& .Mui-selected": { bgcolor: "#F3E8FF !important", color: "#A100FF !important", fontWeight: 700 } }}>
        <ToggleButton value="report"><CalendarMonthIcon sx={{ fontSize: 17 }} /> Monthly Report</ToggleButton>
        <ToggleButton value="brief"><SearchIcon sx={{ fontSize: 17 }} /> Ad-hoc Research</ToggleButton>
      </ToggleButtonGroup>
      {view === "report" ? <MonthlyReport /> : <AdHocBrief />}
    </Box>
  );
}

function AdHocBrief() {
  const [title, setTitle] = useState("");
  const [briefText, setBriefText] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const commission = async () => {
    if (!briefText.trim()) return;
    setStatus("running");
    setError(null);
    setReport(null);
    try {
      const r = await commissionResearch(title.trim() || "Untitled brief", briefText.trim());
      setReport(r);
      setStatus("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Research failed.");
      setStatus("error");
    }
  };

  const reset = () => {
    setStatus("idle");
    setReport(null);
    setError(null);
  };

  return (
    <Box>
      <Typography sx={{ color: "#6E6E6E", mb: 2.5, maxWidth: "72ch", fontSize: 14 }}>
        Commission an investigation. The research agent decomposes your brief into concrete questions,
        queries the contract warehouse to answer each, and synthesises a finished report with sources.
      </Typography>

      {status === "idle" || status === "error" ? (
        <Box sx={{ maxWidth: 760 }}>
          <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: "#6E6E6E", mb: 1.5 }}>
            Commission a brief
          </Typography>
          <Card elevation={0} sx={{ border: "1px solid #E4E4E4" }}>
            <CardContent>
              <Typography sx={{ fontSize: 12, color: "#6E6E6E", mb: 0.5 }}>Title</Typography>
              <InputBase
                fullWidth
                placeholder="e.g. Cyber capability spend — agency breakdown FY24–25"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                sx={{ fontSize: 14, mb: 2, pb: 1, borderBottom: "1px solid #E4E4E4" }}
              />
              <Typography sx={{ fontSize: 12, color: "#6E6E6E", mt: 2, mb: 0.5 }}>Research brief</Typography>
              <Box
                component={TextareaAutosize}
                minRows={5}
                placeholder={`Describe what you need to know and why it matters.\n\nExample: ${EXAMPLE_BRIEF}`}
                value={briefText}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setBriefText(e.target.value)}
                style={{
                  width: "100%", fontFamily: "inherit", fontSize: 14, color: "#3C3C3C",
                  border: "none", outline: "none", resize: "none", background: "transparent", lineHeight: 1.65,
                  boxSizing: "border-box",
                }}
              />
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2 }}>
                <Typography sx={{ fontSize: 12, color: "#6E6E6E" }}>
                  Grounded entirely in the AusTender contract warehouse. Takes ~30–60 seconds.
                </Typography>
                <Button
                  variant="contained"
                  disableElevation
                  disabled={!briefText.trim()}
                  onClick={commission}
                  startIcon={<AutoAwesomeIcon />}
                  sx={{ bgcolor: "#A100FF", "&:hover": { bgcolor: "#7500C0" }, textTransform: "none", fontWeight: 600, flexShrink: 0 }}
                >
                  Commission
                </Button>
              </Box>
              {error && <Typography sx={{ fontSize: 13, color: "#C62828", mt: 1.5 }}>{error}</Typography>}
            </CardContent>
          </Card>
        </Box>
      ) : status === "running" ? (
        <Card elevation={0} sx={{ border: "1px solid #E4E4E4", bgcolor: "#F7F5FA", maxWidth: 760 }}>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1.5 }}>
              <CircularProgress size={18} sx={{ color: "#A100FF" }} />
              <Typography sx={{ fontWeight: 600, fontSize: 15 }}>Researching…</Typography>
            </Box>
            <Typography sx={{ fontSize: 13.5, color: "#6E6E6E", lineHeight: 1.6, mb: 2 }}>
              Planning the investigation, querying the contract warehouse, and synthesising findings.
              This usually takes 30–60 seconds.
            </Typography>
            <LinearProgress sx={{ borderRadius: 1, "& .MuiLinearProgress-bar": { bgcolor: "#A100FF" }, bgcolor: "#EADCFA" }} />
          </CardContent>
        </Card>
      ) : report ? (
        <Box sx={{ maxWidth: 860 }}>
          {/* Report header */}
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 2, mb: 2 }}>
            <Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                <ArticleOutlinedIcon sx={{ fontSize: 18, color: "#A100FF" }} />
                <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: "#A100FF", fontWeight: 700 }}>
                  Research Report
                </Typography>
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>{report.title}</Typography>
            </Box>
            <Button onClick={reset} size="small" sx={{ textTransform: "none", color: "#6E6E6E", flexShrink: 0 }}>
              New brief
            </Button>
          </Box>

          {/* Executive summary */}
          <Card elevation={0} sx={{ border: "1px solid #E4E4E4", mb: 2 }}>
            <CardContent>
              <Typography sx={{ fontSize: 11, letterSpacing: ".1em", textTransform: "uppercase", color: "#6E6E6E", mb: 1 }}>
                Executive Summary
              </Typography>
              <Typography sx={{ fontSize: 14.5, lineHeight: 1.7, color: "#2A2A2A" }}>{report.executive_summary}</Typography>
            </CardContent>
          </Card>

          {/* Findings */}
          <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: "#6E6E6E", mb: 1.5 }}>
            Findings
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 3 }}>
            {report.findings.map((f, i) => (
              <Card key={i} elevation={0} sx={{ border: "1px solid #E4E4E4" }}>
                <CardContent sx={{ "&:last-child": { pb: 2 } }}>
                  <Typography sx={{ fontSize: 13.5, fontWeight: 700, color: "#1A1A1A", mb: 0.75 }}>
                    {i + 1}. {f.question}
                  </Typography>
                  <Typography sx={{ fontSize: 14, lineHeight: 1.65, color: "#3C3C3C" }}>{f.finding}</Typography>
                  {f.sources.length > 0 && (
                    <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", mt: 1.25 }}>
                      {f.sources.map((s) => (
                        <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: 10.5, height: 20, borderColor: "#E4E4E4", color: "#6E6E6E" }} />
                      ))}
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>

          {/* Recommendation */}
          {report.recommendation && (
            <Card elevation={0} sx={{ border: "1px solid #A100FF", bgcolor: "rgba(161,0,255,.03)", mb: 2 }}>
              <CardContent>
                <Typography sx={{ fontSize: 11, letterSpacing: ".1em", textTransform: "uppercase", color: "#A100FF", fontWeight: 700, mb: 1 }}>
                  Recommendation
                </Typography>
                <Typography sx={{ fontSize: 14.5, lineHeight: 1.7, color: "#2A2A2A" }}>{report.recommendation}</Typography>
              </CardContent>
            </Card>
          )}

          {report.sources.length > 0 && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
              <Typography sx={{ fontSize: 11, color: "#6E6E6E", letterSpacing: ".1em", textTransform: "uppercase" }}>Sources</Typography>
              {report.sources.map((s) => (
                <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: 11, height: 20, borderColor: "#E4E4E4", color: "#6E6E6E" }} />
              ))}
            </Box>
          )}
        </Box>
      ) : null}
    </Box>
  );
}
