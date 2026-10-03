import { NavLink } from "react-router-dom";
import { NETWORKS, useNetwork } from "../context/NetworkContext.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Network Map", icon: "grid" },
  { to: "/station", label: "Station Detail", icon: "pin" },
  { to: "/classification", label: "Classification", icon: "layers" },
  { to: "/forecasting", label: "Forecasting", icon: "trend" },
  { to: "/interventions", label: "Interventions", icon: "wrench" },
  { to: "/interchange", label: "Interchange Sync", icon: "swap" },
  { to: "/festivals", label: "Festival Impact", icon: "spark" },
  { to: "/future-impact", label: "Future Impact", icon: "spark", mumbaiOnly: true },
  { to: "/models", label: "Model Comparison", icon: "compare" },
];

const ICONS = {
  grid: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  pin: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" />
      <circle cx="12" cy="9" r="2.4" />
    </svg>
  ),
  layers: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="m12 3 9 5-9 5-9-5 9-5Z" />
      <path d="m3 13 9 5 9-5" />
    </svg>
  ),
  trend: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 17 9 11 13 15 21 6" />
      <path d="M15 6h6v6" />
    </svg>
  ),
  wrench: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2 2.6-2.6Z" />
    </svg>
  ),
  swap: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M7 3v14M7 17 3 13M7 17l4-4" />
      <path d="M17 21V7M17 7l4 4M17 7l-4 4" />
    </svg>
  ),
  spark: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" />
    </svg>
  ),
  compare: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9 3v18M15 3v18M4 8h5M15 8h5M4 16h5M15 16h5" />
    </svg>
  ),
};

const NETWORK_HELP = {
  mumbai69: "Survey-backed main analysis for the original 69 stations.",
  mumbai_future: "Synthetic MMRDA future-line stations. Orange banner marks estimated figures.",
  delhi: "Survey-backed Delhi Red / Yellow / Blue (50 stations, 4,560 responses).",
};

export default function Sidebar() {
  const { network, setNetwork } = useNetwork();
  return (
    <aside
      style={{
        width: 240,
        flexShrink: 0,
        background: "var(--card)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
      }}
    >
      <div style={{ padding: "22px 20px 18px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "var(--accent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 700,
              fontSize: 15,
            }}
          >
            M
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: -0.2 }}>MetroOpt</div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Resource Optimization</div>
          </div>
        </div>
      </div>

      <div style={{ padding: "12px 12px 4px", display: "flex", flexDirection: "column", gap: 6 }}>
        <label style={{ fontSize: 10.5, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: 0.4 }}>
          NETWORK
          <select
            value={network}
            onChange={(e) => setNetwork(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 4, padding: "8px 8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--card)", fontSize: 12.5 }}
          >
            {NETWORKS.map((n) => (
              <option key={n.id} value={n.id}>{n.label}</option>
            ))}
          </select>
        </label>
        <p style={{ margin: 0, fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.45 }}>
          {NETWORK_HELP[network]}
        </p>
      </div>

      <nav style={{ padding: 12, display: "flex", flexDirection: "column", gap: 2, flex: 1, overflowY: "auto" }}>
        {NAV_ITEMS.filter((item) => !item.mumbaiOnly || network !== "delhi").map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            style={({ isActive }) => ({
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "9px 12px",
              borderRadius: 8,
              fontSize: 13.5,
              fontWeight: 500,
              color: isActive ? "var(--accent)" : "var(--text-secondary)",
              background: isActive ? "var(--accent-light)" : "transparent",
            })}
          >
            {ICONS[item.icon]}
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ padding: 16, borderTop: "1px solid var(--border)" }}>
        <div style={{ fontSize: 10.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
          Group 7 &middot; K.J. Somaiya
          <br />
          School of Engineering
        </div>
      </div>
    </aside>
  );
}
