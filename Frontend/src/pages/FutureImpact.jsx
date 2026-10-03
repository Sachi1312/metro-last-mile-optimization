import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader, Card } from "../components/ui.jsx";
import FutureImpactPanel from "../components/FutureImpactPanel.jsx";
import { useNetwork } from "../context/NetworkContext.jsx";

const EXPLAIN = [
  {
    title: "What this page answers",
    body: "If MMRDA’s planned lines (2B, 4, 5, 6, 7A, 9, and related) open, how do the existing 69 Mumbai Metro stations change at published interchange points?",
  },
  {
    title: "How the numbers are made",
    body: "Riders on new lines who must change onto Lines 1, 2A, 7, or 3 add footfall at those transfer stations. A few stations may lose a small share because a new line offers another path. Stations with no transfer link stay as today.",
  },
  {
    title: "How to read Low / Middle / High",
    body: "Three demand cases for the same transfer links — conservative, middle, and optimistic. Use Middle as the main figure when discussing results; Low and High show the range.",
  },
  {
    title: "What this is not",
    body: "Not live ticket data and not a claim that every one of the 69 stations changes. It is a model scenario built from published interchange links and scaled ridership assumptions.",
  },
  {
    title: "Why it helps",
    body: "Extra riders imply extra peak trains and last-mile pressure on the current network — so expansion planning can target the stations that actually absorb the new demand.",
  },
];

export default function FutureImpact() {
  const { network } = useNetwork();
  const navigate = useNavigate();

  useEffect(() => {
    if (network === "delhi") navigate("/", { replace: true });
  }, [network, navigate]);

  if (network === "delhi") return null;

  return (
    <div>
      <PageHeader
        title="Future Lines Impact"
        subtitle="Model scenario: how the original 69 stations gain or lose riders when future Mumbai lines open at interchange points."
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        {EXPLAIN.map((item) => (
          <Card key={item.title} style={{ padding: "14px 16px" }}>
            <div style={{ fontSize: 12.5, fontWeight: 700, marginBottom: 6 }}>{item.title}</div>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.55 }}>
              {item.body}
            </p>
          </Card>
        ))}
      </div>

      <FutureImpactPanel />
    </div>
  );
}
