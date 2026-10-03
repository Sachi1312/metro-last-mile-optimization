import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Filler,
} from "chart.js";
import api from "../api.js";
import { Card, PageHeader } from "../components/ui.jsx";
import { Loading, ErrorState } from "../components/StatusStates.jsx";
import SeverityBadge, { severityColor } from "../components/SeverityBadge.jsx";
import { estimateFleetCount, fleetLabel } from "../utils/fleetEstimate.js";
import { roleLabel } from "../utils/roleLabel.js";
import { useNetwork } from "../context/NetworkContext.jsx";
import SyntheticBanner from "../components/SyntheticBanner.jsx";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Filler);

// Hardcoded SHAP-style explanation weights per severity band (illustrative, not fetched from API)
const SHAP_BY_SEVERITY = {
  Critical: [
    { feature: "Auto/cab availability gap", value: 0.31 },
    { feature: "Peak-hour crowding", value: 0.24 },
    { feature: "Walking distance to bus stop", value: 0.19 },
    { feature: "Safety perception score", value: 0.14 },
    { feature: "Bus frequency", value: 0.08 },
    { feature: "Population density", value: 0.04 },
  ],
  High: [
    { feature: "Peak-hour crowding", value: 0.27 },
    { feature: "Auto/cab availability gap", value: 0.23 },
    { feature: "Walking distance to bus stop", value: 0.2 },
    { feature: "Bus frequency", value: 0.15 },
    { feature: "Safety perception score", value: 0.1 },
    { feature: "Population density", value: 0.05 },
  ],
  Medium: [
    { feature: "Walking distance to bus stop", value: 0.26 },
    { feature: "Bus frequency", value: 0.22 },
    { feature: "Auto/cab availability gap", value: 0.19 },
    { feature: "Peak-hour crowding", value: 0.17 },
    { feature: "Safety perception score", value: 0.11 },
    { feature: "Population density", value: 0.05 },
  ],
  Low: [
    { feature: "Bus frequency", value: 0.24 },
    { feature: "Walking distance to bus stop", value: 0.22 },
    { feature: "Population density", value: 0.19 },
    { feature: "Auto/cab availability gap", value: 0.16 },
    { feature: "Peak-hour crowding", value: 0.12 },
    { feature: "Safety perception score", value: 0.07 },
  ],
};

// Illustrative 24h relative-load curve, generated per station (not just per severity band).
// Mumbai Metro operates ~5:30am to ~12:30am — no service 1am-4am (forced to 0).
// Base shape: bimodal commute curve, morning peak ~8-9am, evening peak ~6-7pm.
// Index 0 = 12am ... 23 = 11pm.
const BASE_CURVE = [
  0.06, 0, 0, 0, 0, 0.18, 0.5, 0.85, 1.0, 0.92, 0.68, 0.52, 0.48, 0.5, 0.52, 0.55, 0.6, 0.72, 0.98, 0.9, 0.62, 0.38, 0.2, 0.1,
];

// Role-driven shape adjustments: office-heavy stations get sharper, narrower commute
// peaks; residential/mixed stations get a flatter, broader curve; interchanges keep
// meaningful midday and off-peak transfer traffic.
function roleShapeFactor(role) {
  if (!role) return 1.0;
  if (role.startsWith("office")) return 0.75;
  if (role.startsWith("interchange") || role === "terminus_interchange") return 1.15;
  if (role === "airport" || role === "airport_adj") return 1.3;
  return 1.05;
}

function interchangeMiddayBump(isInterchange) {
  return isInterchange ? [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 12, 12, 10, 8, 0, 0, 0, 0, 0, 0, 0, 0] : new Array(24).fill(0);
}

// Small deterministic per-station jitter so stations sharing a role/severity don't render
// pixel-identical bars, without breaking the realistic commute-hour shape.
function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function buildPeakHourPattern(stationInfo, lmpi) {
  const crowding = typeof lmpi?.crowding_score === "number" ? lmpi.crowding_score : 50;
  const amplitude = 45 + crowding * 0.55; // ~45-100 ceiling, scaled by actual crowding score
  const roleFactor = roleShapeFactor(stationInfo?.role);
  const midday = interchangeMiddayBump(stationInfo?.is_interchange);
  const seed = hashSeed(stationInfo?.station_name || "");

  return BASE_CURVE.map((base, i) => {
    if (i >= 1 && i <= 4) return 0; // no service overnight
    const jitter = ((seed >> (i % 24)) % 9) - 4; // deterministic -4..+4
    const shaped = Math.pow(base, roleFactor) * amplitude + midday[i] + jitter;
    return Math.max(0, Math.min(100, Math.round(shaped)));
  });
}

const HOURS = Array.from({ length: 24 }, (_, i) => (i === 0 ? "12am" : i < 12 ? `${i}am` : i === 12 ? "12pm" : `${i - 12}pm`));

const FACTORS = [
  { key: "auto_problem_score", label: "Auto/Cab Access" },
  { key: "walking_problem_score", label: "Walking Distance" },
  { key: "bus_problem_score", label: "Bus Connectivity" },
  { key: "crowding_score", label: "Crowding" },
  { key: "safety_score", label: "Safety" },
];

export default function StationDetail() {
  const { expansion } = useNetwork();
  if (expansion) return <ExpansionStationDetail />;
  return <MumbaiStationDetail />;
}

function ExpansionStationDetail() {
  const { network, synthetic, surveyBacked } = useNetwork();
  const { name } = useParams();
  const [stations, setStations] = useState(null);
  const [station, setStation] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .expansionStations(network)
      .then((res) => setStations(res.data.stations))
      .catch((e) => setError(e.message));
  }, [network]);

  useEffect(() => {
    const target = name || stations?.[0]?.station_name;
    if (!target) return;
    api
      .expansionStation(target, network)
      .then((res) => setStation(res.data))
      .catch((e) => setError(e.message));
  }, [name, network, stations]);

  if (error) return <ErrorState message={error} />;
  if (!station) return <Loading label="Loading station" />;

  return (
    <div>
      <PageHeader
        title={station.station_name}
        subtitle={`Line ${station.line} · ${station.discovered_cluster}`}
        right={
          stations && (
            <select
              value={station.station_name}
              onChange={(e) => navigate(`/station/${encodeURIComponent(e.target.value)}`)}
              style={{ padding: "9px 14px", borderRadius: 8, border: "1px solid var(--border)", minWidth: 220 }}
            >
              {stations.map((s) => (
                <option key={s.station_name} value={s.station_name}>{s.station_name}</option>
              ))}
            </select>
          )
        }
      />
      {synthetic && (
        <SyntheticBanner>
          LMPI is the formula estimated from station facts. Opt-in is a transfer prediction from the Mumbai survey model, not a local survey.
        </SyntheticBanner>
      )}
      {network === "delhi" && surveyBacked && (
        <div style={{ padding: "12px 16px", background: "#EEF6FF", border: "1px solid #90CAF9", borderRadius: 8, fontSize: 12.5, lineHeight: 1.55, marginBottom: 18 }}>
          <strong>Survey-backed LMPI. </strong>
          Factor scores come from Delhi passenger responses. Daily ridership remains a scenario scale.
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>LMPI index</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{station.lmpi_score}</div>
          <SeverityBadge severity={station.severity_label} />
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Chance a commuter opts in</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{Math.round(station.opt_in_probability * 100)}%</div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Scenario daily riders</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{station.daily_riders.toLocaleString()}</div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Peak trains/hr</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700 }}>{station.recommended_trains_hr}</div>
        </Card>
      </div>
      <Card style={{ padding: 16, marginTop: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Suggested actions</h3>
        {station.interventions.map((iv) => (
          <div key={iv.intervention} style={{ fontSize: 13, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 600 }}>{iv.intervention}</div>
            {iv.peak_window && (
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>Peak: {iv.peak_window}</div>
            )}
            {iv.rationale && (
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>{iv.rationale}</div>
            )}
            {(iv.fleet_count || iv.estimated_cost_lakhs) && (
              <div style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 2 }}>
                {iv.fleet_count ? `≈ ${iv.fleet_count} ${iv.fleet_type || "vehicles"}` : null}
                {iv.fleet_count && iv.estimated_cost_lakhs ? " · " : null}
                {iv.estimated_cost_lakhs != null ? `Rs ${iv.estimated_cost_lakhs} L` : null}
              </div>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}

function MumbaiStationDetail() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [allStations, setAllStations] = useState(null);
  const [selected, setSelected] = useState(name || "");
  const [data, setData] = useState(null);
  const [forecast30, setForecast30] = useState(null);
  const [forecastMonthly, setForecastMonthly] = useState(null);
  const [forecast2026Daily, setForecast2026Daily] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .stations()
      .then((res) => {
        setAllStations(res.data.stations);
        if (!name && res.data.stations.length) {
          setSelected(res.data.stations[0].station_name);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (name) setSelected(name);
  }, [name]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([api.station(selected), api.forecast30(selected), api.forecast2026(selected)])
      .then(([sRes, fRes, mRes]) => {
        if (cancelled) return;
        setData(sRes.data);
        setForecast30(fRes.data.daily_forecast);
        setForecastMonthly(mRes.data.monthly_summary);
        setForecast2026Daily(mRes.data.daily_forecast);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const handleSelect = (e) => {
    const val = e.target.value;
    setSelected(val);
    navigate(`/station/${encodeURIComponent(val)}`);
  };

  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <PageHeader
        title="Station Detail"
        subtitle="Per-station diagnostics — factor breakdown, model explanation, hourly load, and forecast"
        right={
          allStations && (
            <select
              value={selected}
              onChange={handleSelect}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--card)",
                fontSize: 13.5,
                fontWeight: 500,
                minWidth: 220,
              }}
            >
              {allStations.map((s) => (
                <option key={s.station_name} value={s.station_name}>
                  {s.station_name} ({s.severity_label})
                </option>
              ))}
            </select>
          )
        }
      />

      {(loading || !data) && !error ? (
        <Loading label={`Loading ${selected || "station"}`} />
      ) : (
        <StationBody
          data={data}
          forecast30={forecast30}
          forecastMonthly={forecastMonthly}
          forecast2026Daily={forecast2026Daily}
        />
      )}
    </div>
  );
}

function StationBody({ data, forecast30, forecastMonthly, forecast2026Daily }) {
  if (!data) return null;
  const { station_info, lmpi, frequency, interventions } = data;
  const severity = lmpi?.severity_label || "Medium";
  const color = severityColor(severity);
  const shap = SHAP_BY_SEVERITY[severity] || SHAP_BY_SEVERITY.Medium;
  const heat = useMemo(() => buildPeakHourPattern(station_info, lmpi), [station_info, lmpi]);

  const morningPeak = frequency?.find((f) => f.time_window === "morning_peak");

  return (
    <div>
      <Card style={{ padding: "20px 24px", marginBottom: 20, borderLeft: `4px solid ${color}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ fontSize: 19, fontWeight: 700 }}>{station_info?.station_name}</h2>
              <SeverityBadge severity={severity} />
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
              Line {station_info?.line} · {roleLabel(station_info?.role)}
              {station_info?.is_interchange ? " · Interchange" : ""}
            </div>
          </div>
          <div style={{ display: "flex", gap: 28 }}>
            <MiniStat label="LMPI Score" value={lmpi?.lmpi_score ?? "—"} />
            <MiniStat label="Recommended Mode" value={lmpi?.recommended_last_mile ?? "—"} small />
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 20, marginBottom: 20 }}>
        <Card style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>LMPI Factor Breakdown</h3>
          {FACTORS.map((f) => (
            <FactorBar key={f.key} label={f.label} value={lmpi?.[f.key]} color={color} />
          ))}
        </Card>

        <Card style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Model Explanation (SHAP)</h3>
          <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
            Relative contribution to severity classification
          </p>
          {shap.map((f) => (
            <FactorBar key={f.feature} label={f.feature} value={f.value * 100} max={35} color="var(--accent)" />
          ))}
        </Card>
      </div>

      <Card style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Peak Hour Load Pattern</h3>
        <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginBottom: 16 }}>
          Relative footfall intensity by hour of day — illustrative curve shaped by this station's role and crowding score
        </p>
        <div style={{ display: "flex", gap: 3, height: 90 }}>
          {heat.map((v, i) => (
            <div
              key={i}
              style={{
                flex: 1,
                height: "100%",
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-end",
                alignItems: "center",
              }}
            >
              <div
                title={`${HOURS[i]}: ${v}`}
                style={{
                  width: "100%",
                  height: `${v}%`,
                  background: color,
                  opacity: 0.35 + (v / 100) * 0.65,
                  borderRadius: 2,
                }}
              />
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 3, marginTop: 6 }}>
          {HOURS.map((h, i) => (
            <div
              key={h}
              style={{
                flex: 1,
                fontSize: 8.5,
                color: "var(--text-secondary)",
                textAlign: "center",
                visibility: i % 3 === 0 ? "visible" : "hidden",
              }}
            >
              {h}
            </div>
          ))}
        </div>
      </Card>

      <Card style={{ padding: 20, marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Footfall Forecast</h3>
        <ForecastChart
          data={forecast30}
          monthly={forecastMonthly}
          daily2026={forecast2026Daily}
          color={color}
          stationName={station_info?.station_name}
          role={station_info?.role}
          isInterchange={station_info?.is_interchange}
        />
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
        <Card style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 14 }}>Top Recommended Interventions</h3>
          {interventions && interventions.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {interventions.map((iv, i) => (
                <div
                  key={i}
                  style={{
                    padding: "10px 14px",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12.5,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{iv.intervention}</div>
                  <div style={{ color: "var(--text-secondary)", marginTop: 3 }}>
                    Impact {iv.impact_score} · Est. cost Rs {iv.estimated_cost_lakhs} lakhs
                    {(() => {
                      const est = estimateFleetCount(iv.intervention, iv.estimated_cost_lakhs);
                      return est ? ` · ≈ ${est.count} ${fleetLabel(est.type)}` : "";
                    })()}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>No interventions on record.</div>
          )}
        </Card>

        <Card style={{ padding: 20, background: "var(--accent-light)", border: "1px solid var(--accent)" }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, color: "var(--accent)" }}>
            Frequency Recommendation
          </h3>
          {morningPeak ? (
            <>
              <div className="mono" style={{ fontSize: 30, fontWeight: 700, color: "var(--accent)" }}>
                {morningPeak.recommended_trains_hr} trains/hr
              </div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 4 }}>
                Current: {morningPeak.current_trains_hr} trains/hr ({morningPeak.delta_trains_hr > 0 ? "+" : ""}
                {morningPeak.delta_trains_hr})
              </div>
              <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 2 }}>
                Headway: {morningPeak.recommended_headway_min} min · Morning peak
              </div>
            </>
          ) : (
            <div style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>No frequency data available.</div>
          )}
        </Card>
      </div>
    </div>
  );
}

function MiniStat({ label, value, small }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>{label}</div>
      <div className={small ? "" : "mono"} style={{ fontSize: small ? 14 : 22, fontWeight: 700, marginTop: 2 }}>
        {value}
      </div>
    </div>
  );
}

function FactorBar({ label, value, max = 100, color }) {
  const v = typeof value === "number" ? value : 0;
  const pct = Math.min(100, (v / max) * 100);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: "var(--text-secondary)" }}>{label}</span>
        <span className="mono" style={{ fontWeight: 600 }}>
          {typeof value === "number" ? value.toFixed(1) : "—"}
        </span>
      </div>
      <div style={{ height: 6, background: "#EEF1F6", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

const PERIODS = [
  { label: "7D", days: 7 },
  { label: "14D", days: 14 },
  { label: "30D", days: 30 },
];

// Short calendar-style label with weekday — used on chart axes, e.g. "Fri 24 Apr"
function formatShortDate(dateStr) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}

// Full calendar-style label with day name — used in tooltip titles, e.g. "Wed, 1 Jan 2026"
function formatFullDate(dateStr) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

function formatDateRange(data) {
  if (!data || data.length === 0) return "";
  const first = formatShortDate(data[0].date);
  const last = formatShortDate(data[data.length - 1].date);
  return `${first} – ${last}`;
}

// Role-aware demand reasoning — combines day type (weekday/weekend/festival/holiday) with
// what kind of station this is, since the same calendar day drives opposite demand at
// different station types (e.g. New Year: office stations go quiet, transit/leisure hubs surge).
function demandContext(role, isInterchange, { isFestival, festivalName, dayType } = {}) {
  const isOfficeHeavy = role && role.startsWith("office");
  const isLeisureHub = role && ["shopping_hub", "religious_tourist", "commercial", "airport", "airport_adj"].includes(role);
  const isResidential = role && role.startsWith("residential");
  const isWeekend = dayType === "weekend";

  if (isFestival) {
    const label = festivalName ? `${festivalName}` : "Festival/holiday";
    if (isOfficeHeavy) return `${label} — office commute suppressed, expect lower-than-usual demand here`;
    if (isInterchange) return `${label} — leisure/transit surge likely as travelers pass through this interchange`;
    if (isLeisureHub) return `${label} — leisure and travel surge expected at this station`;
    if (isResidential) return `${label} — local family/leisure travel, moderate surge likely`;
    return `${label} — demand pattern likely deviates from a normal weekday`;
  }
  if (isWeekend) {
    if (isOfficeHeavy) return "Weekend — office commute drops sharply here";
    if (isLeisureHub) return "Weekend — leisure footfall typically rises here";
    return "Weekend — lower routine commute demand";
  }
  return "Weekday — regular commute pattern";
}

function weekdayReasoning(dateStr, role, isInterchange) {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return "";
  const day = d.getDay(); // 0 = Sunday, 6 = Saturday
  const dayType = day === 0 || day === 6 ? "weekend" : "weekday";
  return demandContext(role, isInterchange, { isFestival: false, dayType });
}

function ForecastChart({ data, monthly, daily2026, color, stationName, role, isInterchange }) {
  const [mode, setMode] = useState("daily");
  const [periodDays, setPeriodDays] = useState(30);
  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyPeriod, setHistoryPeriod] = useState(null); // { year, month }
  const [month2026, setMonth2026] = useState("January");
  const [avp, setAvp] = useState(null);
  const [avpLoading, setAvpLoading] = useState(false);
  const [avpError, setAvpError] = useState(null);

  useEffect(() => {
    setHistory(null);
    setHistoryPeriod(null);
    setAvp(null);
    setMode("daily");
  }, [stationName]);

  const loadHistory = (year, month) => {
    if (!stationName) return;
    setHistoryLoading(true);
    setHistoryError(null);
    api
      .historical(stationName, year, month)
      .then((res) => {
        setHistory(res.data);
        setHistoryPeriod({ year: res.data.selected_year, month: res.data.selected_month });
      })
      .catch((e) => setHistoryError(e.message))
      .finally(() => setHistoryLoading(false));
  };

  const switchToHistory = () => {
    setMode("history");
    if (!history) loadHistory();
  };

  const switchToActualVsPredicted = () => {
    setMode("avp");
    if (avp || !data || data.length === 0 || !stationName) return;
    const first = new Date(data[0].date);
    const year = first.getFullYear();
    const month = first.getMonth() + 1;
    setAvpLoading(true);
    setAvpError(null);
    api
      .historical(stationName, year, month)
      .then((res) => setAvp({ actual: res.data.daily, year, month }))
      .catch((e) => setAvpError(e.message))
      .finally(() => setAvpLoading(false));
  };

  const windowed = useMemo(() => {
    if (!data) return null;
    return data.slice(Math.max(0, data.length - periodDays));
  }, [data, periodDays]);

  const dailyChartData = useMemo(() => {
    if (!windowed || windowed.length === 0) return null;
    return {
      labels: windowed.map((d) => formatShortDate(d.date)),
      datasets: [
        {
          label: "Forecasted footfall",
          data: windowed.map((d) => d.forecasted_footfall),
          borderColor: color,
          backgroundColor: `${color}22`,
          fill: true,
          tension: 0.35,
          pointRadius: periodDays <= 14 ? 3 : 2,
          pointHoverRadius: 5,
        },
      ],
    };
  }, [windowed, color, periodDays]);

  const dailyChartOptions = useMemo(
    () => ({
      ...dailyOptions,
      plugins: {
        ...dailyOptions.plugins,
        tooltip: {
          callbacks: {
            title: (items) => {
              const point = windowed?.[items[0]?.dataIndex];
              return point ? formatFullDate(point.date) : "";
            },
            label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders`,
            afterLabel: (ctx) => {
              const point = windowed?.[ctx.dataIndex];
              return point ? weekdayReasoning(point.date, role, isInterchange) : "";
            },
          },
        },
      },
    }),
    [windowed, role, isInterchange]
  );

  const monthlyChartData = useMemo(() => {
    if (!monthly || monthly.length === 0) return null;
    return {
      labels: monthly.map((m) => m.month),
      datasets: [
        {
          label: "Avg daily footfall",
          data: monthly.map((m) => m.avg_footfall),
          backgroundColor: color,
          borderRadius: 4,
          maxBarThickness: 56,
        },
      ],
    };
  }, [monthly, color]);

  const historyChartData = useMemo(() => {
    if (!history || !history.daily || history.daily.length === 0) return null;
    return {
      labels: history.daily.map((d) => formatShortDate(d.date)),
      datasets: [
        {
          label: "Actual footfall",
          data: history.daily.map((d) => d.footfall),
          borderColor: color,
          backgroundColor: `${color}18`,
          fill: true,
          tension: 0.3,
          pointRadius: history.daily.map((d) => (d.is_festival ? 5 : d.rain_intensity !== "none" ? 4 : 2)),
          pointBackgroundColor: history.daily.map((d) =>
            d.is_festival ? "#BA7517" : d.rain_intensity !== "none" ? "#1565C0" : color
          ),
          pointHoverRadius: 6,
        },
      ],
    };
  }, [history, color]);

  const historyChartOptions = useMemo(
    () => ({
      ...dailyOptions,
      plugins: {
        ...dailyOptions.plugins,
        tooltip: {
          callbacks: {
            title: (items) => {
              const d = history?.daily?.[items[0]?.dataIndex];
              return d ? formatFullDate(d.date) : "";
            },
            label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders`,
            afterLabel: (ctx) => {
              const d = history?.daily?.[ctx.dataIndex];
              if (!d) return "";
              const lines = [
                demandContext(role, isInterchange, {
                  isFestival: !!d.is_festival,
                  festivalName: d.festival_name,
                  dayType: d.day_type,
                }),
              ];
              if (d.rain_intensity && d.rain_intensity !== "none") lines.push(`Monsoon: ${d.rain_intensity} rain (${d.rainfall_mm}mm)`);
              return lines;
            },
          },
        },
      },
    }),
    [history, role, isInterchange]
  );

  const monthDaily2026 = useMemo(() => {
    if (!daily2026) return [];
    return daily2026.filter((d) => d.month_name === month2026);
  }, [daily2026, month2026]);

  const daily2026ChartData = useMemo(() => {
    if (monthDaily2026.length === 0) return null;
    return {
      labels: monthDaily2026.map((d) => formatShortDate(d.date)),
      datasets: [
        {
          label: "Forecasted footfall",
          data: monthDaily2026.map((d) => d.forecasted_footfall),
          borderColor: color,
          backgroundColor: `${color}18`,
          fill: true,
          tension: 0.3,
          pointRadius: monthDaily2026.map((d) => (d.is_festival ? 5 : d.is_public_holiday ? 4 : 2)),
          pointBackgroundColor: monthDaily2026.map((d) => (d.is_festival ? "#BA7517" : d.is_public_holiday ? "#8e44ad" : color)),
          pointHoverRadius: 6,
        },
      ],
    };
  }, [monthDaily2026, color]);

  const daily2026ChartOptions = useMemo(
    () => ({
      ...dailyOptions,
      plugins: {
        ...dailyOptions.plugins,
        tooltip: {
          callbacks: {
            title: (items) => {
              const d = monthDaily2026[items[0]?.dataIndex];
              return d ? formatFullDate(d.date) : "";
            },
            label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders`,
            afterLabel: (ctx) => {
              const d = monthDaily2026[ctx.dataIndex];
              if (!d) return "";
              const lines = [
                demandContext(role, isInterchange, {
                  isFestival: !!d.is_festival || !!d.is_public_holiday,
                  festivalName: d.is_festival ? d.festival_name : d.is_public_holiday ? "Public holiday" : null,
                  dayType: d.day_type,
                }),
                `Reliability: ${d.reliability}`,
              ];
              return lines;
            },
          },
        },
      },
    }),
    [monthDaily2026, role, isInterchange]
  );

  // Actual vs predicted: overlay real historical footfall against the model's forecast
  // for the same date range (the 30-day forecast window, e.g. April 2025), to visually
  // sanity-check the forecast against what actually happened.
  const avpChartData = useMemo(() => {
    if (!avp || !data) return null;
    const actualByDate = new Map(avp.actual.map((d) => [d.date, d.footfall]));
    const merged = data
      .map((d) => ({ date: d.date.slice(0, 10), predicted: d.forecasted_footfall, actual: actualByDate.get(d.date.slice(0, 10)) }))
      .filter((d) => d.actual !== undefined);
    if (merged.length === 0) return null;
    return {
      merged,
      chart: {
        labels: merged.map((d) => formatShortDate(d.date)),
        datasets: [
          {
            label: "Actual",
            data: merged.map((d) => d.actual),
            borderColor: "#0F1923",
            backgroundColor: "transparent",
            tension: 0.3,
            pointRadius: 2,
            pointHoverRadius: 5,
            borderDash: [4, 3],
          },
          {
            label: "Predicted",
            data: merged.map((d) => d.predicted),
            borderColor: color,
            backgroundColor: `${color}18`,
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            pointHoverRadius: 5,
          },
        ],
      },
    };
  }, [avp, data, color]);

  const avpMape = useMemo(() => {
    if (!avpChartData) return null;
    const errors = avpChartData.merged.map((d) => Math.abs(d.actual - d.predicted) / d.actual);
    return ((errors.reduce((a, b) => a + b, 0) / errors.length) * 100).toFixed(2);
  }, [avpChartData]);

  const avpChartOptions = useMemo(
    () => ({
      ...dailyOptions,
      plugins: {
        ...dailyOptions.plugins,
        legend: { display: true, labels: { font: { family: "Inter", size: 11 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            title: (items) => {
              const point = avpChartData?.merged?.[items[0]?.dataIndex];
              return point ? formatFullDate(point.date) : "";
            },
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} riders`,
          },
        },
      },
    }),
    [avpChartData]
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, marginBottom: 6 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {PERIODS.map((p) => (
            <FilterPill key={p.label} active={mode === "daily" && periodDays === p.days} onClick={() => { setMode("daily"); setPeriodDays(p.days); }}>
              {p.label}
            </FilterPill>
          ))}
          <FilterPill active={mode === "monthly"} onClick={() => setMode("monthly")}>
            2026 Outlook
          </FilterPill>
          <FilterPill active={mode === "2026"} onClick={() => setMode("2026")}>
            2026 Daily
          </FilterPill>
          <FilterPill active={mode === "history"} onClick={switchToHistory}>
            History
          </FilterPill>
          <FilterPill active={mode === "avp"} onClick={switchToActualVsPredicted}>
            Actual vs Predicted
          </FilterPill>
        </div>
        {mode === "history" && history ? (
          <MonthYearPicker
            availableMonths={history.available_months}
            year={historyPeriod?.year}
            month={historyPeriod?.month}
            onChange={(y, m) => loadHistory(y, m)}
          />
        ) : mode === "2026" ? (
          <div style={{ display: "flex", gap: 4 }}>
            {["January", "February", "March", "April", "May", "June"].map((m) => (
              <button
                key={m}
                onClick={() => setMonth2026(m)}
                style={{
                  padding: "4px 8px",
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 500,
                  border: "1px solid var(--border)",
                  background: month2026 === m ? "var(--accent-light)" : "var(--card)",
                  color: month2026 === m ? "var(--accent)" : "var(--text-secondary)",
                }}
              >
                {m.slice(0, 3)}
              </button>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>
            {mode === "daily"
              ? formatDateRange(windowed)
              : mode === "monthly"
              ? "Jan – Jun 2026"
              : mode === "avp" && avp
              ? `${formatDateRange(data)} · MAPE ${avpMape}%`
              : ""}
          </div>
        )}
      </div>

      {mode === "daily" &&
        (!dailyChartData ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>No forecast data available.</div>
        ) : (
          <div style={{ height: 280 }}>
            <Line data={dailyChartData} options={dailyChartOptions} />
          </div>
        ))}

      {mode === "monthly" &&
        (!monthlyChartData ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>No monthly forecast available.</div>
        ) : (
          <div style={{ height: 280 }}>
            <Bar data={monthlyChartData} options={monthlyOptions} />
          </div>
        ))}

      {mode === "2026" &&
        (!daily2026ChartData ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>No daily 2026 forecast available.</div>
        ) : (
          <>
            <div style={{ height: 280 }}>
              <Line data={daily2026ChartData} options={daily2026ChartOptions} />
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 11, color: "var(--text-secondary)", marginTop: 12 }}>
              <LegendDot color="#BA7517" label="Festival day" />
              <LegendDot color="#8e44ad" label="Public holiday" />
            </div>
          </>
        ))}

      {mode === "history" && (
        <HistoryView
          loading={historyLoading}
          error={historyError}
          chartData={historyChartData}
          chartOptions={historyChartOptions}
          history={history}
        />
      )}

      {mode === "avp" &&
        (avpLoading ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>Loading actual footfall for comparison...</div>
        ) : avpError ? (
          <div style={{ color: "var(--critical)", fontSize: 12.5, padding: "40px 0" }}>{avpError}</div>
        ) : !avpChartData ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>
            No overlapping actual data found for the forecast window.
          </div>
        ) : (
          <>
            <div style={{ height: 280 }}>
              <Line data={avpChartData.chart} options={avpChartOptions} />
            </div>
            <p style={{ fontSize: 11.5, color: "var(--text-secondary)", marginTop: 10 }}>
              Dashed black line is real historical footfall for these dates; the filled line is what the XGBoost model predicted ahead of
              time. Mean Absolute Percentage Error for this window: <strong>{avpMape}%</strong>.
            </p>
          </>
        ))}
    </div>
  );
}

function MonthYearPicker({ availableMonths, year, month, onChange }) {
  if (!availableMonths || availableMonths.length === 0) return null;
  const current = year && month ? `${year}-${String(month).padStart(2, "0")}` : "";
  return (
    <select
      value={current}
      onChange={(e) => {
        const [y, m] = e.target.value.split("-").map(Number);
        onChange(y, m);
      }}
      style={{
        padding: "5px 10px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--card)",
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      {availableMonths.map((m) => (
        <option key={m} value={m}>
          {new Date(`${m}-01T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}
        </option>
      ))}
    </select>
  );
}

function HistoryView({ loading, error, chartData, chartOptions, history }) {
  if (loading) return <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>Loading historical data...</div>;
  if (error) return <div style={{ color: "var(--critical)", fontSize: 12.5, padding: "40px 0" }}>{error}</div>;
  if (!chartData) return <div style={{ color: "var(--text-secondary)", fontSize: 12.5, padding: "40px 0" }}>No historical data available.</div>;

  return (
    <div>
      <div style={{ height: 280, marginBottom: 16 }}>
        <Line data={chartData} options={chartOptions} />
      </div>
      <div style={{ display: "flex", gap: 16, fontSize: 11, color: "var(--text-secondary)", marginBottom: 16 }}>
        <LegendDot color="#BA7517" label="Festival day" />
        <LegendDot color="#1565C0" label="Monsoon / rain day" />
      </div>
      {history?.top_festivals?.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
          <EventList title="Biggest Festival Boosts (all-time)" items={history.top_festivals.map((f) => ({
            label: f.festival_name,
            date: formatShortDate(f.date),
            detail: `+${Math.round(f.festival_boost * 100)}% · ${f.footfall.toLocaleString()} riders`,
          }))} />
          <EventList title="Heaviest Monsoon Days (all-time)" items={history.top_monsoon_days.map((d) => ({
            label: `${d.rain_intensity} rain`,
            date: formatShortDate(d.date),
            detail: `${d.rainfall_mm}mm · ${d.footfall.toLocaleString()} riders`,
          }))} />
        </div>
      )}
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      {label}
    </div>
  );
}

function EventList({ title, items }) {
  return (
    <div>
      <div style={{ fontSize: 11.5, fontWeight: 600, marginBottom: 8 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((it, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 12,
              padding: "6px 10px",
              border: "1px solid var(--border)",
              borderRadius: 6,
            }}
          >
            <span style={{ fontWeight: 500 }}>
              {it.label} <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}>· {it.date}</span>
            </span>
            <span className="mono" style={{ color: "var(--text-secondary)" }}>{it.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FilterPill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 12px",
        borderRadius: 20,
        fontSize: 12,
        fontWeight: 500,
        border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
        background: active ? "var(--accent-light)" : "var(--card)",
        color: active ? "var(--accent)" : "var(--text-secondary)",
      }}
    >
      {children}
    </button>
  );
}

const dailyOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders`,
      },
    },
  },
  scales: {
    x: {
      ticks: { maxTicksLimit: 8, font: { family: "Inter", size: 10 } },
      grid: { display: false },
    },
    y: {
      ticks: {
        font: { family: "JetBrains Mono", size: 10 },
        callback: (v) => v.toLocaleString(),
      },
      grid: { color: "#EEF1F6" },
    },
  },
};

const monthlyOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.parsed.y.toLocaleString()} riders/day avg`,
      },
    },
  },
  scales: {
    x: {
      ticks: { font: { family: "Inter", size: 11 } },
      grid: { display: false },
    },
    y: {
      ticks: {
        font: { family: "JetBrains Mono", size: 10 },
        callback: (v) => v.toLocaleString(),
      },
      grid: { color: "#EEF1F6" },
    },
  },
};
