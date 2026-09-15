import { Box, Button, Card, CardContent, Chip, Typography } from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboard";
import RadarIcon from "@mui/icons-material/Radar";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";
import DescriptionIcon from "@mui/icons-material/Description";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED, CARD_BORDER } from "../theme/dashboardStyles";

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

export function LandingPage({ onNavigate }: { onNavigate: (tab: number) => void }) {
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
    </Box>
  );
}
