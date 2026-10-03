// Literal hex values (not CSS var() references) so these are safe to use in both
// inline styles (with alpha suffixes) and Chart.js canvas contexts, which cannot resolve CSS variables.
const COLORS = {
  Critical: "#E24B4A",
  High: "#EF9F27",
  Medium: "#BA7517",
  Low: "#1D9E75",
};

export function severityColor(severity) {
  return COLORS[severity] || "#4A5568";
}

const LINE_COLORS = {
  1: "#e67e22",
  "2A": "#27ae60",
  "2B": "#f1c40f",
  3: "#2980b9",
  4: "#16a085",
  5: "#1abc9c",
  6: "#e84393",
  7: "#8e44ad",
  "7A": "#9b59b6",
  9: "#c0392b",
  Red: "#e74c3c",
  Yellow: "#f1c40f",
  Blue: "#2980b9",
};

export function lineColor(line) {
  return LINE_COLORS[line] || "#4A5568";
}

export default function SeverityBadge({ severity }) {
  const color = severityColor(severity);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontSize: 11,
        fontWeight: 600,
        padding: "3px 9px",
        borderRadius: 20,
        color,
        background: `${color}18`,
        border: `1px solid ${color}33`,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color }} />
      {severity || "Unknown"}
    </span>
  );
}
