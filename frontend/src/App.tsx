import { useState } from "react";
import { ThemeProvider, CssBaseline, Box, Tab, Tabs, Typography, AppBar, Toolbar } from "@mui/material";
import { theme } from "./theme";
import { LandingPage } from "./pages/LandingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ConversePage } from "./pages/ConversePage";
import { ResearchPage } from "./pages/ResearchPage";
import { OpportunitiesPage } from "./pages/OpportunitiesPage";
import { FeedbackPage } from "./pages/FeedbackPage";

const TABS = [
  { label: "Overview", description: "Start here" },
  { label: "Dashboard", description: "Market position" },
  { label: "Opportunities", description: "Live pipeline" },
  { label: "Ask", description: "Query the data" },
  { label: "Research", description: "Monthly reporting" },
  { label: "Feedback", description: "Improve the tool" },
];

export function App() {
  const [tab, setTab] = useState(0);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>

        {/* Nav — light editorial header matching the static dashboards */}
        <AppBar position="static" elevation={0} sx={{ bgcolor: "#fff", borderBottom: "1px solid #e5e7eb" }}>
          <Toolbar sx={{ gap: 2, minHeight: "56px !important", maxWidth: 1480, mx: "auto", width: "100%" }}>
            <Typography
              onClick={() => setTab(0)}
              sx={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.01em", color: "#A100FF", cursor: "pointer" }}
            >
              TAMBI 2026
            </Typography>
            <Typography sx={{ fontSize: 13, color: "#667085", flexGrow: 1 }}>
              Defence Contract Intelligence
            </Typography>
            <Typography sx={{ fontSize: 12, color: "#98A2B3", letterSpacing: ".1em", textTransform: "uppercase" }}>
              Accenture ANZ
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Tabs */}
        <Box sx={{ bgcolor: "#fff", borderBottom: "1px solid #e5e7eb", position: "sticky", top: 0, zIndex: 10 }}>
          <Box sx={{ maxWidth: 1480, mx: "auto", px: "28px" }}>
            <Tabs
              value={tab}
              onChange={(_, v) => setTab(v)}
              TabIndicatorProps={{ style: { backgroundColor: "#A100FF", height: 2 } }}
              sx={{ "& .MuiTab-root": { color: "#667085", minHeight: 60 }, "& .Mui-selected": { color: "#A100FF !important" } }}
            >
              {TABS.map((t, i) => (
                <Tab
                  key={i}
                  label={
                    <Box sx={{ textAlign: "left" }}>
                      <Box sx={{ fontWeight: 600 }}>{t.label}</Box>
                      <Box sx={{ fontSize: 10, letterSpacing: ".08em", color: "inherit", opacity: .55, textTransform: "uppercase", mt: -.2 }}>
                        {t.description}
                      </Box>
                    </Box>
                  }
                />
              ))}
            </Tabs>
          </Box>
        </Box>

        {/* Page content */}
        <Box sx={{ flexGrow: 1, bgcolor: "background.default" }}>
          <Box sx={{ maxWidth: 1480, mx: "auto", px: "28px", py: "28px" }}>
            {tab === 0 && <LandingPage onNavigate={setTab} />}
            {tab === 1 && <DashboardPage />}
            {tab === 2 && <OpportunitiesPage />}
            {tab === 3 && <ConversePage />}
            {tab === 4 && <ResearchPage />}
            {tab === 5 && <FeedbackPage />}
          </Box>
        </Box>

      </Box>
    </ThemeProvider>
  );
}
