import { Tooltip } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

export function InfoTooltip({ text }: { text: string }) {
  return (
    <Tooltip title={text} arrow placement="right"
      componentsProps={{ tooltip: { sx: { fontSize: 12, maxWidth: 320, lineHeight: 1.55, bgcolor: "#1F2937", "& .MuiTooltip-arrow": { color: "#1F2937" } } } }}>
      <HelpOutlineIcon sx={{ fontSize: 14, color: "#C4B5FD", cursor: "help", ml: 0.75, verticalAlign: "middle", flexShrink: 0,
        "&:hover": { color: "#A100FF" }, transition: "color .12s" }} />
    </Tooltip>
  );
}
