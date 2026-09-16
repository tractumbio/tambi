import { useState } from "react";
import {
  Box, Button, Card, CardContent, Chip, CircularProgress, TextField, Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import FeedbackOutlinedIcon from "@mui/icons-material/FeedbackOutlined";
import { submitFeedback } from "../api/feedback";
import { ACCENTURE_COLOR } from "../theme/competitorColors";
import { CARD_SX, INK_MUTED } from "../theme/dashboardStyles";

const PROMPTS = [
  "Something felt off or confusing",
  "A metric or chart I'd love to see",
  "A competitor or agency missing from the data",
  "The AI summary quality",
  "Something that worked really well",
];

export function FeedbackPage() {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!text.trim()) return;
    setSending(true); setError(null);
    try {
      await submitFeedback(text.trim());
      setSent(true);
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed — please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 720, mx: "auto" }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Chip label="TAMBI 2026" size="small"
          sx={{ bgcolor: "#F5F3FF", color: ACCENTURE_COLOR, fontWeight: 700, fontSize: 10.5, letterSpacing: ".08em", mb: 1.5 }} />
        <Typography sx={{ fontSize: 28, fontWeight: 800, letterSpacing: "-.02em", lineHeight: 1.15, mb: 1 }}>
          Share your feedback
        </Typography>
        <Typography sx={{ fontSize: 15, color: INK_MUTED, lineHeight: 1.6 }}>
          What's working, what's confusing, what you'd like to see next — everything is read and used to improve the tool.
        </Typography>
      </Box>

      {sent ? (
        <Card elevation={0} sx={{ ...CARD_SX, bgcolor: "#F0FDF4", borderColor: "#86EFAC" }}>
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <CheckCircleOutlineIcon sx={{ fontSize: 32, color: "#16A34A" }} />
            <Box>
              <Typography sx={{ fontWeight: 700, fontSize: 15, color: "#166534" }}>Feedback received — thank you.</Typography>
              <Typography sx={{ fontSize: 13, color: "#166534", mt: 0.25 }}>
                Your input has been saved and will be reviewed for the next iteration.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Card elevation={0} sx={CARD_SX}>
          <CardContent sx={{ p: "24px !important" }}>
            {/* Prompt chips */}
            <Typography sx={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".08em", color: INK_MUTED, mb: 1.25 }}>
              Quick starters
            </Typography>
            <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap", mb: 2.5 }}>
              {PROMPTS.map((p) => (
                <Chip key={p} label={p} size="small" onClick={() => setText((t) => t ? `${t}\n${p}: ` : `${p}: `)}
                  sx={{ fontSize: 11.5, cursor: "pointer", bgcolor: "#F5F3FF", color: "#4C1D95",
                    "&:hover": { bgcolor: "#EDE9FE" }, border: "1px solid #DDD6FE" }} />
              ))}
            </Box>

            {/* Text area */}
            <TextField
              multiline minRows={6} maxRows={16} fullWidth
              placeholder="Write anything — specific numbers, UI issues, missing data, ideas, or general impressions…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              sx={{ mb: 2, "& textarea": { fontSize: 14, lineHeight: 1.65, fontFamily: "inherit" } }}
            />

            {error && (
              <Typography sx={{ fontSize: 12.5, color: "#C62828", mb: 1.5 }}>{error}</Typography>
            )}

            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
              <Typography sx={{ fontSize: 12, color: INK_MUTED }}>
                {text.length} / 5000 characters
              </Typography>
              <Button
                variant="contained" disableElevation
                onClick={submit}
                disabled={sending || !text.trim() || text.length > 5000}
                startIcon={sending ? <CircularProgress size={14} sx={{ color: "#fff" }} /> : <FeedbackOutlinedIcon />}
                sx={{ bgcolor: ACCENTURE_COLOR, "&:hover": { bgcolor: "#7500C0" }, textTransform: "none", fontWeight: 600, px: 3 }}
              >
                {sending ? "Submitting…" : "Submit feedback"}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {sent && (
        <Box sx={{ mt: 2, textAlign: "center" }}>
          <Button onClick={() => setSent(false)} sx={{ color: ACCENTURE_COLOR, textTransform: "none", fontSize: 13 }}>
            Submit more feedback
          </Button>
        </Box>
      )}
    </Box>
  );
}
