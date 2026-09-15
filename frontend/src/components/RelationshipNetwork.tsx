import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box, Card, CardContent, Checkbox, Chip, FormControlLabel, ListItemText, MenuItem,
  Select, Skeleton, Switch, Table, TableBody, TableCell, TableHead, TableRow,
  TableSortLabel, TextField, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import { getNetwork, getNetworkContracts } from "../api/metrics";
import { useApi } from "../api/useApi";
import { formatAud, formatDate } from "../lib/format";
import { ACCENTURE_COLOR, CHART_NAVY, competitorColor } from "../theme/competitorColors";
import { CARD_SX, INK, INK_MUTED, LABEL_SX } from "../theme/dashboardStyles";
import type { CommonFilterParams, NetworkContractRow, NetworkGraphData, NetworkNode } from "../types";

const W = 940;
const H = 560;
const PAD = 60;
const THEME_COLOR = "#0F766E";

function diamond(cx: number, cy: number, r: number): string {
  return `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`;
}

interface Placed extends NetworkNode {
  x: number;
  y: number;
  r: number;
}

type LayoutMode = "radial" | "bipartite" | "force" | "circle";

// Different ways to organise the network. All deterministic (no randomness) so the layout
// is stable across renders; the user can still drag nodes afterwards.
function layout(
  data: NetworkGraphData,
  mode: LayoutMode,
): { nodes: Placed[]; index: Map<string, number> } {
  const nodes = data.nodes;
  const N = nodes.length;
  const index = new Map(nodes.map((n, i) => [n.id, i]));
  if (N === 0) return { nodes: [], index };

  const maxVal = Math.max(...nodes.map((n) => n.value), 1);
  const radiusOf = (n: NetworkNode) =>
    (n.kind === "competitor" ? 6 : 11) + Math.sqrt(n.value / maxVal) * (n.kind === "competitor" ? 22 : 16);
  const maxEdge = Math.max(...data.edges.map((e) => e.value), 1);
  const cx = W / 2, cy = H / 2;
  const pos = nodes.map(() => ({ x: cx, y: cy }));
  const isHub = (n: NetworkNode) => n.kind !== "competitor";

  if (mode === "bipartite") {
    // Competitors in a left column, Defence hubs in a right column, both sorted by value.
    const col = (pred: (n: NetworkNode) => boolean, x: number) => {
      const items = nodes.map((n, i) => ({ n, i })).filter((e) => pred(e.n))
        .sort((a, b) => b.n.value - a.n.value);
      items.forEach((e, k) => {
        pos[e.i] = { x, y: PAD + (items.length === 1 ? 0.5 : k / (items.length - 1)) * (H - 2 * PAD) };
      });
    };
    col((n) => !isHub(n), W * 0.26);
    col(isHub, W * 0.74);
  } else if (mode === "circle") {
    // Everything on one ring, competitors first then hubs, each ordered by value.
    const ordered = nodes.map((n, i) => ({ n, i }))
      .sort((a, b) => (isHub(a.n) === isHub(b.n) ? b.n.value - a.n.value : isHub(a.n) ? 1 : -1));
    const R = Math.min(W, H) / 2 - PAD;
    ordered.forEach((e, k) => {
      const a = (k / ordered.length) * Math.PI * 2 - Math.PI / 2;
      pos[e.i] = { x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R * 0.9 };
    });
  } else if (mode === "force") {
    // Free Fruchterman–Reingold: no fixed hubs, seeded on a ring.
    nodes.forEach((_, i) => {
      const a = (i / N) * Math.PI * 2;
      pos[i] = { x: cx + Math.cos(a) * (W / 5), y: cy + Math.sin(a) * (H / 5) };
    });
    const k = Math.sqrt((W * H) / N) * 0.62;
    let temp = W / 8;
    for (let iter = 0; iter < 300; iter++) {
      const disp = pos.map(() => ({ x: 0, y: 0 }));
      for (let v = 0; v < N; v++) for (let u = 0; u < N; u++) {
        if (u === v) continue;
        const dx = pos[v].x - pos[u].x, dy = pos[v].y - pos[u].y;
        const d = Math.hypot(dx, dy) || 0.01;
        disp[v].x += (dx / d) * ((k * k) / d);
        disp[v].y += (dy / d) * ((k * k) / d);
      }
      for (const e of data.edges) {
        const a = index.get(e.source), b = index.get(e.target);
        if (a === undefined || b === undefined) continue;
        const dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
        const d = Math.hypot(dx, dy) || 0.01;
        const f = ((d * d) / k) * (0.4 + e.value / maxEdge);
        disp[a].x -= (dx / d) * f; disp[a].y -= (dy / d) * f;
        disp[b].x += (dx / d) * f; disp[b].y += (dy / d) * f;
      }
      for (let v = 0; v < N; v++) {
        disp[v].x += (cx - pos[v].x) * 0.02; disp[v].y += (cy - pos[v].y) * 0.02;
        const d = Math.hypot(disp[v].x, disp[v].y) || 0.01;
        pos[v].x += (disp[v].x / d) * Math.min(d, temp);
        pos[v].y += (disp[v].y / d) * Math.min(d, temp);
      }
      temp *= 0.97;
    }
    const xs = pos.map((p) => p.x), ys = pos.map((p) => p.y);
    const mnx = Math.min(...xs), mxx = Math.max(...xs), mny = Math.min(...ys), mxy = Math.max(...ys);
    const sx = (W - 2 * PAD) / (mxx - mnx || 1), sy = (H - 2 * PAD) / (mxy - mny || 1);
    for (let i = 0; i < N; i++) { pos[i].x = PAD + (pos[i].x - mnx) * sx; pos[i].y = PAD + (pos[i].y - mny) * sy; }
  } else {
    // radial (default): hubs anchored on the rim, competitors relaxed in the interior.
    const ringR = Math.min(W, H) / 2 - PAD - 6;
    const hubs = nodes.map((n, i) => ({ n, i })).filter((h) => isHub(h.n))
      .sort((a, b) => (a.n.kind === b.n.kind ? b.n.value - a.n.value : a.n.kind !== "competitor" ? -1 : 1));
    hubs.forEach((h, k) => {
      const a = (k / Math.max(hubs.length, 1)) * Math.PI * 2 - Math.PI / 2;
      pos[h.i] = { x: cx + Math.cos(a) * ringR, y: cy + Math.sin(a) * ringR * 0.82 };
    });
    const conn = new Map<string, { x: number; y: number; w: number }[]>();
    for (const e of data.edges) {
      const hi = index.get(e.target);
      if (hi === undefined) continue;
      const list = conn.get(e.source) ?? [];
      list.push({ x: pos[hi].x, y: pos[hi].y, w: 0.2 + e.value / maxEdge });
      conn.set(e.source, list);
    }
    const comps = nodes.map((n, i) => ({ n, i })).filter((c) => c.n.kind === "competitor");
    comps.forEach((c, ci) => {
      const links = conn.get(c.n.id) ?? [];
      if (links.length) {
        const sw = links.reduce((s, l) => s + l.w, 0);
        const bx = links.reduce((s, l) => s + l.x * l.w, 0) / sw;
        const by = links.reduce((s, l) => s + l.y * l.w, 0) / sw;
        pos[c.i] = { x: cx + (bx - cx) * 0.6, y: cy + (by - cy) * 0.6 };
      } else {
        const a = (ci / comps.length) * Math.PI * 2;
        pos[c.i] = { x: cx + Math.cos(a) * ringR * 0.25, y: cy + Math.sin(a) * ringR * 0.25 };
      }
    });
    const bary = new Map(comps.map((c) => [c.i, { ...pos[c.i] }]));
    let step = 42;
    for (let iter = 0; iter < 140; iter++) {
      for (const c of comps) {
        let fx = 0, fy = 0;
        for (const o of comps) {
          if (o.i === c.i) continue;
          const dx = pos[c.i].x - pos[o.i].x, dy = pos[c.i].y - pos[o.i].y;
          const d = Math.hypot(dx, dy) || 0.01;
          fx += (dx / d) * (1800 / (d * d)); fy += (dy / d) * (1800 / (d * d));
          const minD = radiusOf(c.n) + radiusOf(o.n) + 14;
          if (d < minD) { fx += (dx / d) * (minD - d) * 0.5; fy += (dy / d) * (minD - d) * 0.5; }
        }
        const b = bary.get(c.i)!;
        fx += (b.x - pos[c.i].x) * 0.05; fy += (b.y - pos[c.i].y) * 0.05;
        const d = Math.hypot(fx, fy) || 0.01;
        pos[c.i].x += (fx / d) * Math.min(d, step); pos[c.i].y += (fy / d) * Math.min(d, step);
        const rx = pos[c.i].x - cx, ry = pos[c.i].y - cy;
        const rr = Math.hypot(rx, ry), lim = ringR - radiusOf(c.n) - 10;
        if (rr > lim) { pos[c.i].x = cx + (rx / rr) * lim; pos[c.i].y = cy + (ry / rr) * lim; }
      }
      step *= 0.985;
    }
  }

  const placed = nodes.map((n, i) => ({ ...n, x: pos[i].x, y: pos[i].y, r: radiusOf(n) }));
  return { nodes: placed, index };
}

function nodeFill(n: NetworkNode): string {
  if (n.kind === "agency" || n.kind === "branch") return CHART_NAVY;
  if (n.kind === "theme") return THEME_COLOR;
  return competitorColor(n.slug);
}

export function RelationshipNetwork({ filter }: { filter?: CommonFilterParams }) {
  const [immediateOnly, setImmediateOnly] = useState(true);
  const [mode, setMode] = useState<LayoutMode>("radial");
  const [firms, setFirms] = useState<string[]>([]); // selected competitor slugs; empty = all
  const { data, loading } = useApi(
    () => getNetwork(immediateOnly, 14, filter),
    [immediateOnly, filter?.theme ?? "all"],
  );
  const [hover, setHover] = useState<string | null>(null);

  // Firms available to pick from (from the full response), sorted by value.
  const availableFirms = useMemo(
    () => (data?.nodes ?? [])
      .filter((n) => n.kind === "competitor")
      .sort((a, b) => b.value - a.value)
      .map((n) => ({ slug: n.slug ?? "", label: n.label })),
    [data],
  );

  // Apply the firm filter client-side: keep chosen competitors, their edges, and the
  // Defence branches/hubs those edges still reach.
  const graph = useMemo(() => {
    if (!data || firms.length === 0) return data;
    const set = new Set(firms);
    const edges = data.edges.filter((e) => set.has(e.source.replace(/^c:/, "")));
    const targets = new Set(edges.map((e) => e.target));
    const nodes = data.nodes.filter((n) =>
      n.kind === "competitor" ? set.has(n.slug ?? "") : targets.has(n.id));
    return { ...data, nodes, edges };
  }, [data, firms]);

  const placed = useMemo(() => (graph ? layout(graph, mode) : null), [graph, mode]);

  // Exact contracts behind the plot (same scope), client-filtered by the firm selector.
  const contracts = useApi(
    () => getNetworkContracts(immediateOnly, 500, filter),
    [immediateOnly, filter?.theme ?? "all"],
  );
  const contractRows = useMemo(() => {
    const list = contracts.data?.items ?? [];
    const set = new Set(firms);
    return firms.length ? list.filter((r) => r.competitor_slug && set.has(r.competitor_slug)) : list;
  }, [contracts.data, firms]);

  // Table search + sort (client-side over the fetched rows).
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" }>({ key: "value_amount", dir: "desc" });
  const toggleSort = (key: string) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));

  const displayRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = contractRows;
    if (q) {
      list = list.filter((r) =>
        [r.cn_id, r.description, r.supplier_name, r.agency_name, r.buyer_division, r.buyer_branch,
         r.service_offering, r.competitor_label, r.title, r.unspsc_code, r.themes.join(" ")]
          .some((v) => (v ?? "").toLowerCase().includes(q)));
    }
    const dir = sort.dir === "asc" ? 1 : -1;
    const val = (r: NetworkContractRow) =>
      sort.key === "themes" ? r.themes.join(",") : (r as unknown as Record<string, unknown>)[sort.key];
    return [...list].sort((a, b) => {
      const va = val(a), vb = val(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      if (typeof va === "boolean" && typeof vb === "boolean") return ((va ? 1 : 0) - (vb ? 1 : 0)) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [contractRows, query, sort]);

  const th = (field: string, label: string, align: "left" | "right" = "left") => (
    <TableCell align={align} sortDirection={sort.key === field ? sort.dir : false}>
      <TableSortLabel active={sort.key === field} direction={sort.key === field ? sort.dir : "asc"}
        onClick={() => toggleSort(field)}>
        {label}
      </TableSortLabel>
    </TableCell>
  );

  // Live node positions (seeded from the layout, then updated by dragging).
  const [pos, setPos] = useState<Record<string, { x: number; y: number }>>({});
  const [drag, setDrag] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!placed) return;
    const seed: Record<string, { x: number; y: number }> = {};
    for (const n of placed.nodes) seed[n.id] = { x: n.x, y: n.y };
    setPos(seed);
  }, [placed]);

  const at = (n: Placed) => pos[n.id] ?? { x: n.x, y: n.y };

  const toSvg = (clientX: number, clientY: number) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: Math.max(0, Math.min(W, ((clientX - rect.left) / rect.width) * W)),
      y: Math.max(0, Math.min(H, ((clientY - rect.top) / rect.height) * H)),
    };
  };

  const adjacency = useMemo(() => {
    const map = new Map<string, Set<string>>();
    const add = (a: string, b: string) => {
      let s = map.get(a);
      if (!s) { s = new Set(); map.set(a, s); }
      s.add(b);
    };
    for (const e of graph?.edges ?? []) { add(e.source, e.target); add(e.target, e.source); }
    return map;
  }, [graph]);

  const isLit = (id: string) =>
    !hover || hover === id || adjacency.get(hover)?.has(id);

  const maxEdge = Math.max(...(graph?.edges ?? []).map((e) => e.value), 1);

  return (
    <Box sx={{ mt: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: ACCENTURE_COLOR, fontSize: 11 }}>
            Relationships
          </Typography>
          <Typography variant="h6">Supplier ↔ Defence Branch Network</Typography>
          <Typography sx={{ fontSize: 13, color: INK_MUTED, mt: .5 }}>
            How Accenture and competitors connect to Defence branches (CASG, Army, DSTG, CIOG…).
            Drag nodes to rearrange; node size = contract value, line weight = relationship value.
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography sx={{ ...LABEL_SX, fontSize: 11 }}>Organise</Typography>
            <ToggleButtonGroup
              size="small" exclusive value={mode}
              onChange={(_, v: LayoutMode | null) => v && setMode(v)}
              sx={{ "& .MuiToggleButton-root.Mui-selected": { color: ACCENTURE_COLOR, borderColor: ACCENTURE_COLOR } }}
            >
              {(["radial", "bipartite", "force", "circle"] as LayoutMode[]).map((m) => (
                <ToggleButton key={m} value={m} sx={{ fontSize: 11, py: .3, px: 1, textTransform: "capitalize" }}>
                  {m}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
          <Select
            multiple displayEmpty size="small" value={firms}
            onChange={(e) => {
              const v = e.target.value;
              const arr = typeof v === "string" ? v.split(",") : v;
              setFirms(arr.includes("__clear__") ? [] : arr);
            }}
            renderValue={(sel) => (
              <Typography sx={{ fontSize: 12, color: INK_MUTED }}>
                {sel.length === 0 ? "All firms" : `${sel.length} firm${sel.length > 1 ? "s" : ""}`}
              </Typography>
            )}
            sx={{ minWidth: 130, bgcolor: "#fff", "& .MuiSelect-select": { py: .6 } }}
            MenuProps={{ PaperProps: { style: { maxHeight: 360 } } }}
          >
            <MenuItem value="__clear__">
              <Typography sx={{ fontSize: 12, color: ACCENTURE_COLOR }}>Clear (show all)</Typography>
            </MenuItem>
            {availableFirms.map((fm) => (
              <MenuItem key={fm.slug} value={fm.slug} sx={{ py: .2 }}>
                <Checkbox size="small" checked={firms.includes(fm.slug)} sx={{ py: .3 }} />
                <ListItemText primaryTypographyProps={{ fontSize: 13 }} primary={fm.label} />
              </MenuItem>
            ))}
          </Select>
          <FormControlLabel
            control={<Switch size="small" checked={immediateOnly} onChange={(e) => setImmediateOnly(e.target.checked)} />}
            label={<Typography sx={{ fontSize: 12, color: INK_MUTED }}>Immediate competition only</Typography>}
          />
        </Box>
      </Box>

      <Card elevation={0} sx={CARD_SX}>
        <CardContent>
          {loading || !placed ? <Skeleton variant="rectangular" height={H} /> :
            placed.nodes.length === 0 ? (
            <Box sx={{ height: 240, display: "flex", alignItems: "center", justifyContent: "center", color: "#98A2B3" }}>
              <Typography sx={{ fontSize: 13 }}>No supplier–agency relationships for this selection</Typography>
            </Box>
          ) : (
            <>
              <Box sx={{ display: "flex", gap: 2.5, mb: 1, flexWrap: "wrap" }}>
                <Legend swatch={ACCENTURE_COLOR} label="Accenture" round />
                <Legend swatch="#9AA4B2" label="Competitor" round />
                <Legend swatch={CHART_NAVY} label="Defence branch" square />
              </Box>
              <Box component="svg" ref={svgRef} viewBox={`0 0 ${W} ${H}`}
                sx={{ width: "100%", height: "auto", display: "block", cursor: drag ? "grabbing" : "default", userSelect: "none" }}
                onMouseMove={(e) => { if (drag) setPos((prev) => ({ ...prev, [drag]: toSvg(e.clientX, e.clientY) })); }}
                onMouseUp={() => setDrag(null)}
                onMouseLeave={() => { setDrag(null); setHover(null); }}>
                {(graph?.edges ?? []).map((e, i) => {
                  const a = placed.nodes[placed.index.get(e.source)!];
                  const b = placed.nodes[placed.index.get(e.target)!];
                  if (!a || !b) return null;
                  const pa = at(a), pb = at(b);
                  const lit = !hover || hover === e.source || hover === e.target;
                  return (
                    <line key={i} x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
                      stroke={a.slug === "accenture" ? ACCENTURE_COLOR : "#5B6472"}
                      strokeWidth={0.7 + (e.value / maxEdge) * 5}
                      strokeOpacity={lit ? (a.slug === "accenture" ? 0.7 : 0.62) : 0.1} />
                  );
                })}
                {placed.nodes.map((n) => {
                  const lit = isLit(n.id);
                  const isAcc = n.slug === "accenture";
                  const p = at(n);
                  return (
                    <g key={n.id} style={{ cursor: drag === n.id ? "grabbing" : "grab", opacity: lit ? 1 : 0.25 }}
                      onMouseEnter={() => { if (!drag) setHover(n.id); }}
                      onMouseDown={(e) => { e.preventDefault(); setDrag(n.id); setHover(n.id); }}>
                      {n.kind === "agency" || n.kind === "branch" ? (
                        <rect x={p.x - n.r} y={p.y - n.r} width={n.r * 2} height={n.r * 2} rx={3}
                          fill={nodeFill(n)} stroke="#fff" strokeWidth={1.5} />
                      ) : n.kind === "theme" ? (
                        <polygon points={diamond(p.x, p.y, n.r + 2)} fill={nodeFill(n)}
                          stroke="#fff" strokeWidth={1.5} />
                      ) : (
                        <circle cx={p.x} cy={p.y} r={n.r} fill={nodeFill(n)}
                          stroke={isAcc ? "#fff" : "#ffffffcc"} strokeWidth={isAcc ? 2.5 : 1} />
                      )}
                      {isAcc && <circle cx={p.x} cy={p.y} r={n.r + 4} fill="none" stroke={ACCENTURE_COLOR} strokeWidth={1.5} strokeOpacity={0.5} />}
                      {n.kind === "agency" || n.kind === "branch" ? (
                        <text x={p.x} y={p.y} textAnchor="middle" dominantBaseline="central"
                          fontSize={9} fontWeight={700} fill="#fff" style={{ pointerEvents: "none" }}>
                          {shorten(n.label)}
                        </text>
                      ) : (n.kind === "theme" || n.r > 12 || hover === n.id) ? (
                        <text x={p.x} y={p.y - n.r - 4} textAnchor="middle"
                          fontSize={n.kind === "competitor" ? 10 : 11}
                          fontWeight={n.kind !== "competitor" || isAcc ? 700 : 400}
                          fill={INK} style={{ pointerEvents: "none" }}>
                          {shorten(n.label)}
                        </text>
                      ) : null}
                      <title>{`${n.label}\n${formatAud(n.value)} · ${n.contract_count} contracts`}</title>
                    </g>
                  );
                })}
              </Box>
              {hover && (() => {
                const n = placed.nodes.find((p) => p.id === hover);
                return n ? (
                  <Chip size="small" label={`${n.label} · ${formatAud(n.value)} · ${n.contract_count} contracts`}
                    sx={{ mt: 1, fontSize: 12, bgcolor: "#f6f8fb", color: INK }} />
                ) : null;
              })()}
            </>
          )}
        </CardContent>
      </Card>

      {/* Exact contract data behind the plot */}
      <Card elevation={0} sx={{ ...CARD_SX, mt: 2 }}>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1, gap: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <Typography sx={LABEL_SX}>Contract detail</Typography>
              <TextField
                size="small" placeholder="Filter contracts…" value={query}
                onChange={(e) => setQuery(e.target.value)}
                sx={{ width: 240, "& .MuiInputBase-input": { fontSize: 13, py: .75 } }}
              />
            </Box>
            <Typography sx={{ fontSize: 12, color: INK_MUTED }}>
              {contracts.loading ? "loading…"
                : `${displayRows.length.toLocaleString()} shown`
                  + (query || firms.length ? ` of ${contractRows.length.toLocaleString()}` : "")
                  + (!firms.length && (contracts.data?.total ?? 0) > (contracts.data?.limit ?? 0)
                    ? ` · top ${contracts.data?.limit} of ${contracts.data?.total.toLocaleString()} by value` : "")}
            </Typography>
          </Box>
          <Box sx={{ maxHeight: 460, overflow: "auto" }}>
            <Table size="small" stickyHeader sx={{ "& td, & th": { whiteSpace: "nowrap" } }}>
              <TableHead>
                <TableRow sx={{ "& th": { ...LABEL_SX, fontSize: 10, bgcolor: "#fff", py: 1, borderBottom: "1px solid #e5e7eb", "& .MuiTableSortLabel-root": { color: "inherit" }, "& .MuiTableSortLabel-root.Mui-active": { color: ACCENTURE_COLOR } } }}>
                  {th("cn_id", "CN ID")}
                  {th("description", "Description")}
                  {th("competitor_label", "Firm")}
                  {th("supplier_name", "Supplier")}
                  {th("agency_name", "Agency")}
                  {th("buyer_division", "Division")}
                  {th("buyer_branch", "Branch")}
                  {th("themes", "Themes")}
                  {th("service_offering", "Service offering")}
                  {th("service_offering_confidence", "Conf.", "right")}
                  {th("is_addressable", "Addr.")}
                  {th("procurement_method", "Method")}
                  {th("unspsc_code", "UNSPSC")}
                  {th("value_amount", "Value", "right")}
                  {th("value_per_year", "Value/yr", "right")}
                  {th("value_currency", "Cur.")}
                  {th("date_published", "Published", "right")}
                  {th("date_signed", "Signed", "right")}
                  {th("period_start", "Start", "right")}
                  {th("period_end", "End", "right")}
                  {th("amendment_count", "Amend.", "right")}
                  {th("title", "Ref")}
                </TableRow>
              </TableHead>
              <TableBody sx={{ "& td": { fontSize: 12.5, color: INK } }}>
                {displayRows.map((r) => (
                  <TableRow key={r.ocid} hover>
                    <TableCell sx={{ color: INK_MUTED, fontVariantNumeric: "tabular-nums" }}>{r.cn_id ?? "—"}</TableCell>
                    <TableCell sx={{ minWidth: 200, maxWidth: 340, whiteSpace: "normal !important", lineHeight: 1.3 }}>{r.description ?? "—"}</TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ width: 9, height: 9, borderRadius: "2px", bgcolor: competitorColor(r.competitor_slug), flexShrink: 0 }} />
                        {r.competitor_label ?? "—"}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }} title={r.supplier_name ?? undefined}>{r.supplier_name ?? "—"}</TableCell>
                    <TableCell sx={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }} title={r.agency_name ?? undefined}>{r.agency_name ?? "—"}</TableCell>
                    <TableCell>{r.buyer_division ?? "—"}</TableCell>
                    <TableCell sx={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis" }} title={r.buyer_branch ?? undefined}>{r.buyer_branch ?? "—"}</TableCell>
                    <TableCell sx={{ color: INK_MUTED }}>{r.themes.length ? r.themes.join(", ") : "—"}</TableCell>
                    <TableCell sx={{ color: INK_MUTED }}>{r.service_offering ?? "—"}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{r.service_offering_confidence ?? "—"}</TableCell>
                    <TableCell>{r.is_addressable ? "Yes" : "No"}</TableCell>
                    <TableCell sx={{ color: INK_MUTED }}>{r.procurement_method ?? "—"}</TableCell>
                    <TableCell sx={{ color: INK_MUTED, fontVariantNumeric: "tabular-nums" }}>{r.unspsc_code ?? "—"}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{formatAud(r.value_amount)}</TableCell>
                    <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", color: INK_MUTED }}>{formatAud(r.value_per_year)}</TableCell>
                    <TableCell sx={{ color: INK_MUTED }}>{r.value_currency ?? "—"}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{formatDate(r.date_published)}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{formatDate(r.date_signed)}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{formatDate(r.period_start)}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{formatDate(r.period_end)}</TableCell>
                    <TableCell align="right" sx={{ color: INK_MUTED }}>{r.amendment_count}</TableCell>
                    <TableCell sx={{ color: INK_MUTED }}>{r.title ?? "—"}</TableCell>
                  </TableRow>
                ))}
                {!contracts.loading && displayRows.length === 0 && (
                  <TableRow><TableCell colSpan={22} sx={{ fontSize: 13, color: "#98A2B3", py: 3, textAlign: "center" }}>
                    No contracts match this filter
                  </TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}

function Legend({ swatch, label, square, diamond: isDiamond }: {
  swatch: string; label: string; square?: boolean; round?: boolean; diamond?: boolean;
}) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: .75 }}>
      <Box sx={{
        width: 11, height: 11, bgcolor: swatch,
        borderRadius: square ? "2px" : "50%",
        transform: isDiamond ? "rotate(45deg)" : "none",
        ...(isDiamond ? { borderRadius: "2px" } : {}),
      }} />
      <Typography sx={{ ...LABEL_SX, fontSize: 11 }}>{label}</Typography>
    </Box>
  );
}

function shorten(label: string): string {
  return label.length > 26 ? `${label.slice(0, 24)}…` : label;
}
