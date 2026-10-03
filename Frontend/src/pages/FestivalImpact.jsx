import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge from "../components/SeverityBadge.jsx";
import { useNetwork } from "../context/NetworkContext.jsx";
import SyntheticBanner from "../components/SyntheticBanner.jsx";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export default function FestivalImpact() {
  const { network, expansion, synthetic, surveyBacked } = useNetwork();
  const [festivals, setFestivals] = useState(null);
  const [selected, setSelected] = useState("");
  const [impact, setImpact] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setFestivals(null);
    setSelected("");
    setImpact(null);
    const request = expansion ? api.expansionFestivals(network) : api.festivals();
    request
      .then((res) => {
        setFestivals(res.data.festivals);
        if (res.data.festivals.length) setSelected(res.data.festivals[0]);
      })
      .catch((e) => setError(e.message));
  }, [network, expansion]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const request = expansion ? api.expansionFestivalImpact(selected, network) : api.festivalImpact(selected);
    request
      .then((res) => !cancelled && setImpact(res.data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected, network, expansion]);

  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <PageHeader
        title="Festival Impact"
        subtitle={
          network === "delhi"
            ? "Festival surge on Delhi stations using Delhi busy-day list. Severity is survey-backed; extra riders use scenario daily levels."
            : synthetic
              ? "Festival surge on this scenario network. Future Mumbai lines use the Mumbai festival list."
              : "Which stations see the biggest festival-day surge and which see the least — so spare trains, autos, and buses shift to where demand actually is"
        }
        right={
          festivals && (
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--card)",
                fontSize: 13.5,
                fontWeight: 500,
                minWidth: 200,
              }}
            >
              {festivals.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          )
        }
      />

      {synthetic && (
        <SyntheticBanner>
          Extra riders are this station&apos;s scenario daily level times the festival percentage. They are not ticket counts.
        </SyntheticBanner>
      )}
      {network === "delhi" && surveyBacked && (
        <div style={{ padding: "12px 16px", background: "#EEF6FF", border: "1px solid #90CAF9", borderRadius: 8, fontSize: 12.5, lineHeight: 1.55, marginBottom: 18 }}>
          <strong>Survey-backed severity; scenario ridership. </strong>
          Extra riders are this station&apos;s scenario daily level times the festival percentage — not DMRC ticket counts.
        </div>
      )}

      {loading || !impact ? (
        <Loading label={`Loading ${selected || "festival"} impact`} />
      ) : (
        <>
          {impact.caveat && (
            <div
              style={{
                padding: "12px 16px",
                background: "#FFF8E8",
                border: "1px solid #EF9F27",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--text-primary)",
                lineHeight: 1.6,
                marginBottom: 20,
              }}
            >
              <strong>Data limitation:</strong> {impact.caveat}
            </div>
          )}

          <Card style={{ padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>
              Extra Riders by Station — {impact.festival}
            </h3>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
              All {impact.station_count} stations, ranked by extra riders vs. each station's own normal-day average
              (network average: +{impact.network_avg_extra_riders?.toLocaleString()} riders).
            </p>
            <RankedChart stations={impact.stations} />
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
            <StationGroup
              title="Highest Surge — Shift Resources Here"
              subtitle="Largest absolute increase in riders — deploy extra trains, autos, and staff here on this festival"
              stations={impact.surge_stations}
              tone="surge"
              networkAvg={impact.network_avg_extra_riders}
              topExtra={impact.stations[0]?.extra_riders}
            />
            <StationGroup
              title="Lowest Surge — Divert Resources From Here"
              subtitle="Smallest increase in riders relative to the rest of the network — safe to trim frequency here and route that capacity to the surge stations instead"
              stations={impact.quiet_stations}
              tone="quiet"
              networkAvg={impact.network_avg_extra_riders}
              topExtra={impact.stations[0]?.extra_riders}
              topStationName={impact.stations[0]?.station_name}
            />
          </div>
        </>
      )}
    </div>
  );
}

function RankedChart({ stations }) {
  const top = stations.slice(0, 20);
  const chartData = {
    labels: top.map((s) => s.station_name),
    datasets: [
      {
        label: "Extra riders",
        data: top.map((s) => s.extra_riders),
        backgroundColor: top.map((s) => (s.extra_riders >= 0 ? "#1D9E75" : "#E24B4A")),
        borderRadius: 4,
        maxBarThickness: 26,
      },
    ],
  };
  return (
    <div style={{ height: 340 }}>
      <Bar
        data={chartData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: "y",
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const s = top[ctx.dataIndex];
                  return `${ctx.parsed.x > 0 ? "+" : ""}${ctx.parsed.x.toLocaleString()} riders vs normal day (${s.avg_festival_boost >= 0 ? "+" : ""}${Math.round(s.avg_festival_boost * 100)}% network rate)`;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { color: "#EEF1F6" },
              ticks: { font: { family: "JetBrains Mono", size: 10 }, callback: (v) => v.toLocaleString() },
            },
            y: {
              grid: { display: false },
              ticks: { font: { family: "Inter", size: 10.5 } },
            },
          },
        }}
      />
    </div>
  );
}

function StationGroup({ title, subtitle, stations, tone, networkAvg, topExtra, topStationName }) {
  const accent = tone === "surge" ? "var(--critical)" : "var(--low)";
  return (
    <Card style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4, color: accent }}>{title}</h3>
      <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: tone === "quiet" ? 8 : 14 }}>{subtitle}</p>
      {tone === "quiet" && topExtra && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6, fontStyle: "italic" }}>
          Spare capacity from these stations can move to {topStationName} and the other surge stations above, which
          see up to {topExtra.toLocaleString()} extra riders.
        </p>
      )}
      {tone === "quiet" && (
        <p style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.5 }}>
          Note: a station's everyday severity rating (Critical/High/etc.) reflects year-round crowding pressure,
          not festival growth. A Critical station can still land here if its normal-day baseline is already so
          high that the festival adds relatively little extra <em>on top</em> — that doesn't mean cutting its
          normal-day resourcing, only that its festival-specific top-up is lower priority than the surge stations.
        </p>
      )}
      {stations.length === 0 ? (
        <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No stations in this group.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {stations.map((s) => (
            <div
              key={s.station_name}
              style={{
                padding: "10px 12px",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${accent}`,
                borderRadius: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12.5, fontWeight: 600 }}>{s.station_name}</span>
                    {s.severity_label && <SeverityBadge severity={s.severity_label} />}
                  </div>
                  <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 2 }}>Line {s.line}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: accent }}>
                    {s.extra_riders >= 0 ? "+" : ""}
                    {s.extra_riders.toLocaleString()}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>riders vs normal day</div>
                  {s.suggested_extra_trains_hr !== null && s.suggested_extra_trains_hr !== undefined && (
                    <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 2 }}>
                      {s.suggested_extra_trains_hr >= 0 ? "+" : ""}
                      {s.suggested_extra_trains_hr} trains/hr
                    </div>
                  )}
                </div>
              </div>
              {tone === "quiet" && networkAvg > 0 && (
                <div style={{ fontSize: 10.5, color: "var(--text-secondary)", marginTop: 6 }}>
                  Only {Math.round((s.extra_riders / networkAvg) * 100)}% of the network's average festival-day
                  surge ({networkAvg.toLocaleString()} riders)
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
