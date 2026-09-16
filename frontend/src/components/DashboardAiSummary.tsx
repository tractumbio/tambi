import { useState } from "react";
import { Box, Button, Card, CardContent, CircularProgress, Divider, Typography } from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { commissionResearch } from "../api/research";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED } from "../theme/dashboardStyles";
import type { CommonFilterParams } from "../types";

export function DashboardAiSummary({ filter }: { filter?: CommonFilterParams }) {
  const [insight, setInsight] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    setInsight(null);
    try {
      const themeClause = filter?.theme ? ` within the ${filter.theme} Defence theme` : "";
      const report = await commissionResearch(
        `Accenture Defence Market Intelligence — Strategic Dashboard Summary${themeClause}`,
        `You are a senior strategy analyst preparing an executive briefing for Accenture's Defence sector leadership. Using the Australian Defence procurement data${themeClause}, provide a comprehensive strategic summary covering:

1. **Market context**: Size and growth of the addressable Defence consulting market, key trends and shifts.
2. **Accenture's position**: Total contract value, number of active contracts, year-on-year momentum, and how Accenture's share has evolved.
3. **Competitive dynamics**: How Accenture stacks up against key competitors (KPMG, Deloitte, EY, PwC, MBB firms) — where Accenture leads, lags, and where there are contested spaces.
4. **Agency relationships**: Which Defence agencies are Accenture's strongest partners and where there are untapped opportunities.
5. **Thematic exposure**: Which Defence capability themes (e.g. cyber, logistics, intelligence, platforms) Accenture is well-positioned in vs underweight.
6. **Strategic watch-list**: The 3-5 most important actions Accenture should take to grow its Defence book of business over the next 12 months.

Be specific, cite patterns from the data, and write at McKinsey executive-summary quality. Avoid generic statements.`,
      );
      setInsight(report.executive_summary + "\n\n" + report.recommendation);
    } catch {
      setInsight("Could not generate AI summary — please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Divider sx={{ mt: 5, mb: 4 }} />
      <Card
        elevation={0}
        sx={{
          ...CARD_SX,
          borderColor: insight ? ACCENTURE_COLOR : undefined,
          bgcolor: insight ? "rgba(161,0,255,.02)" : undefined,
        }}
      >
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: insight ? 2.5 : 0, flexWrap: "wrap", gap: 2 }}>
            <Box>
              <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Claude · Strategic Intelligence</Typography>
              <Typography variant="h6" sx={{ fontWeight: 800 }}>AI Executive Summary</Typography>
              {!insight && (
                <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: 0.5 }}>
                  Claude reads the full dashboard — market, Accenture's position, competitors, relationships, and head-to-head — and synthesises a strategic briefing.
                </Typography>
              )}
            </Box>
            {!insight && (
              <Button
                variant="contained"
                size="medium"
                startIcon={loading ? <CircularProgress size={16} sx={{ color: "#fff" }} /> : <AutoAwesomeIcon />}
                disabled={loading}
                onClick={generate}
                sx={{
                  textTransform: "none", fontSize: 13, fontWeight: 700,
                  bgcolor: ACCENTURE_COLOR, "&:hover": { bgcolor: "#8800dd" },
                  borderRadius: 2, px: 2.5, py: 1, boxShadow: "none",
                  flexShrink: 0,
                }}
              >
                {loading ? "Generating strategic summary…" : "Generate AI Summary"}
              </Button>
            )}
          </Box>

          {insight && (
            <>
              {insight.split("\n\n").map((para, i) => (
                <Typography key={i} sx={{ fontSize: 14.5, lineHeight: 1.8, color: "#111827", mb: 1.5, whiteSpace: "pre-line" }}>
                  {para}
                </Typography>
              ))}
              <Box sx={{ mt: 2, display: "flex", gap: 2 }}>
                <Button
                  size="small"
                  onClick={() => { setInsight(null); generate(); }}
                  startIcon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
                  sx={{ textTransform: "none", fontSize: 12, color: ACCENTURE_COLOR, px: 0 }}
                >
                  Regenerate
                </Button>
                <Button
                  size="small"
                  onClick={() => setInsight(null)}
                  sx={{ textTransform: "none", fontSize: 12, color: INK_MUTED, px: 0 }}
                >
                  Dismiss
                </Button>
              </Box>
            </>
          )}
        </CardContent>
      </Card>
    </>
  );
}
