import { useState } from "react";
import {
  Box, Card, CardContent, Chip, CircularProgress, Collapse, Divider,
  IconButton, InputBase, Link, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CodeIcon from "@mui/icons-material/Code";
import { askMarket, AskResponse } from "../api/ask";
import { VisualStudio } from "../components/VisualStudio";

const EXAMPLE_QUESTIONS = [
  "Which 5 firms have won the most Defence contract value?",
  "How much Defence contract value has Accenture won, and with which agencies?",
  "List the largest contracts expiring in the next 12 months with their CN ids.",
  "Which competitor category (big4, mbb, defence primes) has grown fastest since FY23?",
];

interface Exchange {
  question: string;
  result: AskResponse | null;
  error: string | null;
  loading: boolean;
}

function SqlDetails({ result }: { result: AskResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ mt: 2 }}>
      <Link
        component="button"
        onClick={() => setOpen((o) => !o)}
        sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, fontSize: 11.5, color: "#6E6E6E", textDecoration: "none" }}
      >
        <CodeIcon sx={{ fontSize: 14 }} /> {open ? "Hide" : "View"} query & {result.row_count} row{result.row_count === 1 ? "" : "s"}
      </Link>
      <Collapse in={open}>
        <Box sx={{ mt: 1, p: 1.5, bgcolor: "#0B1220", borderRadius: 1, overflow: "auto" }}>
          <Typography component="pre" sx={{ fontFamily: "monospace", fontSize: 11.5, color: "#A5D6FF", whiteSpace: "pre-wrap", m: 0 }}>
            {result.sql}
          </Typography>
        </Box>
        {result.rows.length > 0 && (
          <Box sx={{ mt: 1, maxHeight: 260, overflow: "auto", border: "1px solid #E4E4E4", borderRadius: 1 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {result.columns.map((c) => (
                    <TableCell key={c} sx={{ fontSize: 11, fontWeight: 700, bgcolor: "#F7F5FA", py: 0.75 }}>{c}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {result.rows.slice(0, 50).map((row, i) => (
                  <TableRow key={i}>
                    {result.columns.map((c) => (
                      <TableCell key={c} sx={{ fontSize: 11.5, py: 0.5 }}>{String(row[c] ?? "—")}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Collapse>
    </Box>
  );
}

function AskPanel() {
  const [input, setInput] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);

  const anyLoading = exchanges.some((e) => e.loading);

  const submit = async (question: string) => {
    const q = question.trim();
    if (!q || anyLoading) return;
    setInput("");
    const idx = exchanges.length;
    setExchanges((prev) => [...prev, { question: q, result: null, error: null, loading: true }]);
    try {
      const result = await askMarket(q);
      setExchanges((prev) => prev.map((e, i) => (i === idx ? { ...e, result, loading: false } : e)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setExchanges((prev) => prev.map((e, i) => (i === idx ? { ...e, error: msg, loading: false } : e)));
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="overline" sx={{ color: "#A100FF", fontSize: 11 }}>Query the Data</Typography>
        <Typography variant="h6" sx={{ fontWeight: 800, fontSize: 17 }}>Ask the Market</Typography>
        <Typography sx={{ color: "#6E6E6E", mt: 0.25, fontSize: 13 }}>
          Natural language → safe SQL → narrated answer with contract sources.
        </Typography>
      </Box>

      {/* Input */}
      <Card elevation={0} sx={{ border: "1px solid #A100FF", mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", px: 2, py: 1 }}>
          <InputBase
            fullWidth
            placeholder="Ask about the Defence contract market…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit(input)}
            disabled={anyLoading}
            sx={{ fontSize: 14, "& input": { py: 1 } }}
          />
          <IconButton onClick={() => submit(input)} disabled={!input.trim() || anyLoading} sx={{ color: "#A100FF" }}>
            {anyLoading ? <CircularProgress size={20} sx={{ color: "#A100FF" }} /> : <ArrowForwardIcon />}
          </IconButton>
        </Box>
      </Card>

      {/* Example questions */}
      {exchanges.length === 0 && (
        <Box>
          <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: "#6E6E6E", mb: 1.5 }}>
            Try asking
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {EXAMPLE_QUESTIONS.map((q) => (
              <Box key={q} onClick={() => submit(q)}
                sx={{ px: 2, py: 1.25, border: "1px solid #E4E4E4", borderRadius: 1, cursor: "pointer",
                  fontSize: 13, color: "#3C3C3C",
                  "&:hover": { borderColor: "#A100FF", color: "#A100FF", bgcolor: "rgba(161,0,255,.03)" },
                  transition: "all .15s" }}>
                {q}
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Conversation */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {exchanges.map((ex, i) => (
          <Box key={i}>
            <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
              <Box sx={{ bgcolor: "#A100FF", color: "#fff", px: 2.5, py: 1.5, borderRadius: 2, maxWidth: "80%", fontSize: 14, fontWeight: 500 }}>
                {ex.question}
              </Box>
            </Box>
            <Card elevation={0} sx={{ border: "1px solid #E4E4E4" }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                  <Box sx={{ width: 8, height: 8, bgcolor: "#A100FF", borderRadius: "50%" }} />
                  <Typography sx={{ fontSize: 11, letterSpacing: ".14em", textTransform: "uppercase", color: "#A100FF", fontWeight: 700 }}>
                    TAMBI · Analysis
                  </Typography>
                </Box>
                {ex.loading && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 1 }}>
                    <CircularProgress size={16} sx={{ color: "#A100FF" }} />
                    <Typography sx={{ fontSize: 14, color: "#6E6E6E" }}>Writing a query and analysing the warehouse…</Typography>
                  </Box>
                )}
                {ex.error && <Typography sx={{ fontSize: 14, color: "#C62828" }}>{ex.error}</Typography>}
                {ex.result && (
                  <>
                    {ex.result.answer.split("\n\n").map((para, j) => (
                      <Typography key={j} sx={{ fontSize: 14.5, lineHeight: 1.7, color: "#3C3C3C", mb: 1.5, whiteSpace: "pre-line" }}>{para}</Typography>
                    ))}
                    {ex.result.sources.length > 0 && (
                      <>
                        <Divider sx={{ my: 2 }} />
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                          <Typography sx={{ fontSize: 11, color: "#6E6E6E", letterSpacing: ".1em", textTransform: "uppercase" }}>Sources</Typography>
                          {ex.result.sources.map((s) => (
                            <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: 11, height: 20, borderColor: "#E4E4E4", color: "#6E6E6E" }} />
                          ))}
                        </Box>
                      </>
                    )}
                    <SqlDetails result={ex.result} />
                  </>
                )}
              </CardContent>
            </Card>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function ConversePage() {
  return (
    <Box>
      {/* Page header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline" sx={{ color: "#A100FF", fontSize: 11 }}>Pillar II</Typography>
        <Typography variant="h5" sx={{ fontWeight: 800 }}>Ask & Visualise</Typography>
        <Typography sx={{ color: "#6E6E6E", mt: 0.5, maxWidth: "68ch", fontSize: 15 }}>
          Ask the warehouse in plain English, or describe any chart and let AI fetch the data and render it — instantly.
        </Typography>
      </Box>

      {/* Two-column split */}
      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1px 1fr", gap: 0, minHeight: 600 }}>
        {/* Left — Ask */}
        <Box sx={{ pr: 3 }}>
          <AskPanel />
        </Box>

        {/* Divider */}
        <Box sx={{ bgcolor: "#E5E7EB" }} />

        {/* Right — Visual Studio */}
        <Box sx={{ pl: 3 }}>
          <VisualStudio />
        </Box>
      </Box>
    </Box>
  );
}
