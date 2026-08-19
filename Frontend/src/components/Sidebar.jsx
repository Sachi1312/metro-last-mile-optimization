import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Network Map", icon: "grid" },
  { to: "/station", label: "Station Detail", icon: "pin" },
  { to: "/classification", label: "Classification", icon: "layers" },
  { to: "/forecasting", label: "Forecasting", icon: "trend" },
  { to: "/interventions", label: "Interventions", icon: "wrench" },
  { to: "/interchange", label: "Interchange Sync", icon: "swap" },
  { to: "/festivals", label: "Festival Impact", icon: "spark" },
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

export default function Sidebar() {
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

      <nav style={{ padding: 12, display: "flex", flexDirection: "column", gap: 2, flex: 1 }}>
        {NAV_ITEMS.map((item) => (
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
