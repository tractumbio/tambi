import { useCallback, useState } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  InputAdornment,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ViewListIcon from "@mui/icons-material/ViewList";
import InsightsIcon from "@mui/icons-material/Insights";
import { useApi } from "../api/useApi";
import { getAtms, AtmStatus } from "../api/opportunities";
import type { AtmRow } from "../api/opportunities";
import { formatDate } from "../lib/format";
import { CARD_SX, LABEL_SX, VALUE_SX, INK_MUTED, CARD_BORDER } from "../theme/dashboardStyles";
import { CapabilityMatch } from "../components/CapabilityMatch";

// ── Stat tile ────────────────────────────────────────────────────────────────

function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Box sx={{ ...CARD_SX, p: "20px 24px", minWidth: 160, flex: "1 1 160px" }}>
      <Typography sx={LABEL_SX}>{label}</Typography>
      <Typography sx={{ ...VALUE_SX, fontSize: 26, mt: 0.5 }}>{value}</Typography>
      {sub && (
        <Typography sx={{ fontSize: 11, color: INK_MUTED, mt: 0.25 }}>{sub}</Typography>
      )}
    </Box>
  );
}

// ── Days-to-close badge ───────────────────────────────────────────────────────

function DaysChip({ days }: { days: number | null }) {
  if (days === null) return <Typography sx={{ color: INK_MUTED, fontSize: 13 }}>—</Typography>;
  const urgent = days <= 7;
  const soon = days <= 21;
  return (
    <Chip
      label={days <= 0 ? "Closing today" : `${days}d`}
      size="small"
      sx={{
        fontSize: 11,
        fontWeight: 700,
        bgcolor: urgent ? "#FEE2E2" : soon ? "#FEF3C7" : "#F0FDF4",
        color: urgent ? "#B91C1C" : soon ? "#92400E" : "#166534",
        border: "none",
      }}
    />
  );
}

// ── ATM type badge ────────────────────────────────────────────────────────────

function TypeChip({ label }: { label: string | null }) {
  if (!label) return null;
  return (
    <Chip
      label={label}
      size="small"
      variant="outlined"
      sx={{ fontSize: 11, borderColor: CARD_BORDER, color: INK_MUTED }}
    />
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function OpportunitiesPage() {
  const [statusFilter, setStatusFilter] = useState<AtmStatus>("open");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"match" | "list">("match");

  const fetcher = useCallback(
    () => getAtms({ defence_only: true, status: statusFilter, limit: 500 }),
    [statusFilter]
  );
  const { data, loading, error } = useApi(fetcher, [statusFilter]);

  const items: AtmRow[] = data?.items ?? [];

  const filtered = search.trim()
    ? items.filter((a) => {
        const q = search.toLowerCase();
        return (
          a.title?.toLowerCase().includes(q) ||
          a.agency_name?.toLowerCase().includes(q) ||
          a.unspsc_title?.toLowerCase().includes(q) ||
          a.atm_type?.toLowerCase().includes(q)
        );
      })
    : items;

  // Summary stats
  const urgentCount = filtered.filter((a) => a.days_to_close !== null && a.days_to_close <= 7).length;
  const closingSoon = filtered.filter((a) => a.days_to_close !== null && a.days_to_close <= 21).length;
  const medianDays =
    filtered.length > 0
      ? (() => {
          const days = filtered
            .map((a) => a.days_to_close)
            .filter((d): d is number => d !== null)
            .sort((a, b) => a - b);
          if (!days.length) return null;
          const mid = Math.floor(days.length / 2);
          return days.length % 2 ? days[mid] : Math.round((days[mid - 1] + days[mid]) / 2);
        })()
      : null;

  return (
    <Box>
      {/* Header row */}
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 2, mb: 3 }}>
        <Typography sx={{ fontWeight: 800, fontSize: 20, letterSpacing: "-.01em" }}>
          Live Opportunities
        </Typography>
        <Typography sx={{ fontSize: 13, color: INK_MUTED }}>
          Defence ATMs · sourced from AusTender
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_, v) => v && setView(v)}
          sx={{
            ml: "auto",
            "& .MuiToggleButton-root": { fontSize: 12, px: 1.5, textTransform: "none", color: INK_MUTED, gap: 0.5 },
            "& .Mui-selected": { bgcolor: "#F3E8FF !important", color: "#A100FF !important", fontWeight: 700 },
          }}
        >
          <ToggleButton value="match"><InsightsIcon sx={{ fontSize: 16 }} /> Capability Match</ToggleButton>
          <ToggleButton value="list"><ViewListIcon sx={{ fontSize: 16 }} /> List</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {view === "match" ? (
        <>
          {/* Status filter for match view */}
          <Box sx={{ display: "flex", gap: 2, alignItems: "center", mb: 2 }}>
            <ToggleButtonGroup
              size="small"
              exclusive
              value={statusFilter}
              onChange={(_, v) => v && setStatusFilter(v)}
              sx={{
                "& .MuiToggleButton-root": { fontSize: 12, px: 2, textTransform: "none", color: INK_MUTED },
                "& .Mui-selected": { bgcolor: "#F3E8FF !important", color: "#A100FF !important", fontWeight: 700 },
              }}
            >
              <ToggleButton value="open">Open</ToggleButton>
              <ToggleButton value="closed">Closed</ToggleButton>
              <ToggleButton value="all">All</ToggleButton>
            </ToggleButtonGroup>
            <Typography sx={{ fontSize: 12, color: INK_MUTED }}>
              Fit = semantic match of each opportunity's description against the firm's actual delivered Defence work, refined by UNSPSC category. Prior agency relationship is shown as a tick, not scored.
            </Typography>
          </Box>
          <CapabilityMatch statusFilter={statusFilter} />
        </>
      ) : (
      <>
      {/* Stat tiles */}
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
        <StatTile label="Total shown" value={loading ? "…" : filtered.length} sub="Defence ATMs" />
        <StatTile
          label="Closing ≤ 7 days"
          value={loading ? "…" : urgentCount}
          sub="Act now"
        />
        <StatTile
          label="Closing ≤ 21 days"
          value={loading ? "…" : closingSoon}
          sub="On radar"
        />
        <StatTile
          label="Median days to close"
          value={loading || medianDays === null ? "—" : `${medianDays}d`}
          sub="open ATMs"
        />
      </Box>

      {/* Filters row */}
      <Box sx={{ display: "flex", gap: 2, alignItems: "center", mb: 2, flexWrap: "wrap" }}>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={statusFilter}
          onChange={(_, v) => v && setStatusFilter(v)}
          sx={{
            "& .MuiToggleButton-root": { fontSize: 12, px: 2, textTransform: "none", color: INK_MUTED },
            "& .Mui-selected": { bgcolor: "#F3E8FF !important", color: "#A100FF !important", fontWeight: 700 },
          }}
        >
          <ToggleButton value="open">Open</ToggleButton>
          <ToggleButton value="closed">Closed</ToggleButton>
          <ToggleButton value="all">All</ToggleButton>
        </ToggleButtonGroup>

        <TextField
          size="small"
          placeholder="Search title, agency, category…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 280, "& .MuiOutlinedInput-root": { fontSize: 13 } }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ fontSize: 16, color: INK_MUTED }} />
              </InputAdornment>
            ),
          }}
        />

        {data && (
          <Typography sx={{ fontSize: 12, color: INK_MUTED, ml: "auto" }}>
            {filtered.length} of {data.total} ATMs
          </Typography>
        )}
      </Box>

      {/* Table */}
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress size={32} sx={{ color: "#A100FF" }} />
        </Box>
      ) : error ? (
        <Typography sx={{ color: "#B91C1C", fontSize: 13, py: 4 }}>{error}</Typography>
      ) : filtered.length === 0 ? (
        <Typography sx={{ color: INK_MUTED, fontSize: 13, py: 4 }}>No ATMs found.</Typography>
      ) : (
        <TableContainer
          component={Paper}
          elevation={0}
          sx={{ ...CARD_SX, overflow: "hidden" }}
        >
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow sx={{ "& th": { bgcolor: "#F9FAFB", fontWeight: 700, fontSize: 11, letterSpacing: ".04em", textTransform: "uppercase", color: INK_MUTED, borderBottom: `1px solid ${CARD_BORDER}`, py: "10px" } }}>
                <TableCell sx={{ minWidth: 280 }}>Title / Agency</TableCell>
                <TableCell sx={{ minWidth: 140 }}>Category</TableCell>
                <TableCell sx={{ width: 110 }}>Type</TableCell>
                <TableCell sx={{ width: 100 }}>Published</TableCell>
                <TableCell sx={{ width: 100 }}>Closes</TableCell>
                <TableCell sx={{ width: 90 }} align="center">Days left</TableCell>
                <TableCell sx={{ width: 48 }} />
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((atm) => (
                <TableRow
                  key={atm.atm_id}
                  sx={{
                    "&:last-child td": { border: 0 },
                    "&:hover": { bgcolor: "#F9FAFB" },
                    "& td": { fontSize: 13, py: "10px", borderColor: CARD_BORDER },
                  }}
                >
                  {/* Title + agency */}
                  <TableCell>
                    <Typography sx={{ fontWeight: 600, fontSize: 13, lineHeight: 1.3, color: "#111827" }}>
                      {atm.title ?? atm.atm_id}
                    </Typography>
                    {atm.agency_name && (
                      <Typography sx={{ fontSize: 12, color: INK_MUTED, mt: 0.25 }}>
                        {atm.agency_name}
                        {atm.location_state ? ` · ${atm.location_state}` : ""}
                      </Typography>
                    )}
                    {atm.description && (
                      <Tooltip title={atm.description} arrow placement="bottom-start">
                        <Typography
                          sx={{
                            fontSize: 11,
                            color: INK_MUTED,
                            mt: 0.25,
                            maxWidth: 420,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            cursor: "default",
                          }}
                        >
                          {atm.description}
                        </Typography>
                      </Tooltip>
                    )}
                  </TableCell>

                  {/* UNSPSC category */}
                  <TableCell>
                    {atm.unspsc_title ? (
                      <Tooltip title={atm.unspsc_code ?? ""} arrow>
                        <Typography sx={{ fontSize: 12, color: "#111827" }}>
                          {atm.unspsc_title}
                        </Typography>
                      </Tooltip>
                    ) : (
                      <Typography sx={{ fontSize: 12, color: INK_MUTED }}>
                        {atm.unspsc_code ?? "—"}
                      </Typography>
                    )}
                  </TableCell>

                  {/* ATM type */}
                  <TableCell>
                    <TypeChip label={atm.atm_type} />
                  </TableCell>

                  {/* Dates */}
                  <TableCell sx={{ color: INK_MUTED }}>{formatDate(atm.published_date)}</TableCell>
                  <TableCell sx={{ fontWeight: atm.days_to_close !== null && atm.days_to_close <= 7 ? 700 : 400 }}>
                    {formatDate(atm.close_date)}
                  </TableCell>

                  {/* Days to close */}
                  <TableCell align="center">
                    <DaysChip days={atm.days_to_close} />
                  </TableCell>

                  {/* External link */}
                  <TableCell align="center">
                    {atm.url ? (
                      <Link href={atm.url} target="_blank" rel="noopener noreferrer" sx={{ color: INK_MUTED, display: "flex", justifyContent: "center" }}>
                        <OpenInNewIcon sx={{ fontSize: 15 }} />
                      </Link>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Divider sx={{ mt: 4, mb: 2 }} />
      <Typography sx={{ fontSize: 11, color: INK_MUTED }}>
        Source: AusTender ATM RSS + detail pages · Defence-only filter applied · Sorted by close date ascending
      </Typography>
      </>
      )}
    </Box>
  );
}
