import { useMemo, useState } from "react";
import { Box, FormControl, MenuItem, Select, Typography } from "@mui/material";
import { getFilters } from "../api/contracts";
import { AddressableMarket } from "../components/AddressableMarket";
import { CompetitivePosition } from "../components/CompetitivePosition";
import { RelationshipNetwork } from "../components/RelationshipNetwork";
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

      {/* Accenture's current positioning (addressable market) */}
      <AddressableMarket filter={filter} />

      {/* Accenture vs peer cohorts (Big 4, MBB, challengers) */}
      <CompetitivePosition filter={filter} />

      {/* Supplier <-> Defence agency relationship network */}
      <RelationshipNetwork filter={filter} />
    </Box>
  );
}
