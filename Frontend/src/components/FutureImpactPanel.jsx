import { useEffect, useState } from "react";
import api from "../api.js";
import { Card } from "./ui.jsx";
import { Loading, ErrorState } from "./StatusStates.jsx";

export default function FutureImpactPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .expansionFutureImpact()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading future-line impact" />;

  const gain = data.rows.filter((r) => r.extra_mid > 0);
  const loss = data.rows.filter((r) => r.extra_mid < 0);
  const added = gain.reduce((sum, r) => sum + r.extra_mid, 0);
  const trains = gain.reduce((sum, r) => sum + r.extra_trains_mid, 0);

  return (
    <Card style={{ padding: 18, marginBottom: 18 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>If the future Mumbai lines open</h3>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.55, marginBottom: 12 }}>
        {data.share_note} {data.unaffected_note} Middle-case total at the stations that gain:{" "}
        <strong>+{added.toLocaleString()} riders/day</strong>, about <strong>+{trains} peak trains</strong>.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 8,
          marginBottom: 14,
          fontSize: 11.5,
          color: "var(--text-secondary)",
          lineHeight: 1.45,
        }}
      >
        <div><strong style={{ color: "var(--text)" }}>Low</strong> — conservative extra riders/day</div>
        <div><strong style={{ color: "var(--text)" }}>Middle</strong> — main case to discuss</div>
        <div><strong style={{ color: "var(--text)" }}>High</strong> — optimistic extra riders/day</div>
        <div><strong style={{ color: "var(--text)" }}>Extra peak trains</strong> — from the middle case</div>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
            <th style={{ padding: "6px 8px" }}>Station</th>
            <th style={{ padding: "6px 8px" }}>Line</th>
            <th style={{ padding: "6px 8px", textAlign: "right" }}>Low</th>
            <th style={{ padding: "6px 8px", textAlign: "right" }}>Middle</th>
            <th style={{ padding: "6px 8px", textAlign: "right" }}>High</th>
            <th style={{ padding: "6px 8px", textAlign: "right" }}>Extra peak trains</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.station_name} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "8px" }}>{r.station_name}</td>
              <td style={{ padding: "8px" }}>{r.line}</td>
              <td className="mono" style={{ padding: "8px", textAlign: "right" }}>{r.extra_low.toLocaleString()}</td>
              <td className="mono" style={{ padding: "8px", textAlign: "right", fontWeight: 700 }}>{r.extra_mid.toLocaleString()}</td>
              <td className="mono" style={{ padding: "8px", textAlign: "right" }}>{r.extra_high.toLocaleString()}</td>
              <td className="mono" style={{ padding: "8px", textAlign: "right" }}>{r.extra_trains_mid ? `+${r.extra_trains_mid}` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {loss.length > 0 && (
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 10 }}>
          {loss.map((r) => r.station_name).join(", ")} {loss.length === 1 ? "loses" : "lose"} some riders because a new line offers another path.
        </p>
      )}
    </Card>
  );
}
