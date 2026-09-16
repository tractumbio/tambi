import { useMemo, useState } from "react";
import { Box, Divider, FormControl, MenuItem, Select, Typography } from "@mui/material";
import { getFilters } from "../api/contracts";
import { AccenturePosition } from "../components/AccenturePosition";
import { AddressableMarket } from "../components/AddressableMarket";
import { CompetitivePosition } from "../components/CompetitivePosition";
import { RelationshipNetwork } from "../components/RelationshipNetwork";
import { HeadToHead } from "../components/HeadToHead";
import { useApi } from "../api/useApi";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { INK_MUTED } from "../theme/dashboardStyles";
import type { CommonFilterParams } from "../types";

export function DashboardPage() {
  const [theme, setTheme] = useState<string>("");
  const filter: CommonFilterParams = useMemo(() => (theme ? { theme } : {}), [theme]);

  const filters = useApi(getFilters, []);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", mb: 3 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>Market Position</Typography>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>Intelligence Dashboard</Typography>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: .5 }}>
            Accenture's position in the addressable Defence services market.
          </Typography>
        </Box>
        <FormControl size="small">
          <Select
            value={theme}
            displayEmpty
            onChange={(e) => setTheme(e.target.value)}
            sx={{ fontSize: 13, minWidth: 190, bgcolor: "#fff" }}
          >
            <MenuItem value=""><em>All Defence themes</em></MenuItem>
            {filters.data?.themes.map((t) => (
              <MenuItem key={t.slug} value={t.slug} sx={{ fontSize: 13 }}>{t.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Section 1 — Defence Expenditure on Consulting (market-level, no Accenture numbers) */}
      <AddressableMarket filter={filter} />

      {/* Section 2 — Accenture's Position */}
      <Divider sx={{ mt: 5, mb: 1 }} />
      <AccenturePosition filter={filter} />

      {/* Section 3 — Competitive landscape: Accenture vs peer cohorts */}
      <Divider sx={{ mt: 5, mb: 1 }} />
      <CompetitivePosition filter={filter} />

      {/* Supplier <-> Defence agency relationship network */}
      <RelationshipNetwork filter={filter} />

      <Divider sx={{ mt: 5, mb: 1 }} />

      {/* Head-to-head firm comparison */}
      <HeadToHead filter={filter} />
    </Box>
  );
}
