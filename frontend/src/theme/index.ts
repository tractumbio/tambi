import { createTheme } from "@mui/material/styles";

// Theme aligned to the previous-analytics static dashboards: Arial type on a light
// #f6f8fb ground, Accenture purple accent, rounded white cards, slate secondary ink.
export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#A100FF", dark: "#7500C0", contrastText: "#fff" },
    secondary: { main: "#4C1D95" },
    background: { default: "#f6f8fb", paper: "#FFFFFF" },
    text: { primary: "#111827", secondary: "#667085" },
    divider: "#e5e7eb",
  },
  typography: {
    fontFamily: ["Arial", "Helvetica", "system-ui", "sans-serif"].join(","),
    h1: { fontSize: 30, fontWeight: 800, letterSpacing: "-0.02em" },
    h5: { fontWeight: 800, letterSpacing: "-0.02em" },
    h6: { fontWeight: 700 },
    overline: { letterSpacing: "0.1em", fontWeight: 700 },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiTab: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, fontSize: 14, minWidth: 120 },
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiCard: { styleOverrides: { root: { boxShadow: "0 1px 2px rgba(0,0,0,0.04)" } } },
  },
});
