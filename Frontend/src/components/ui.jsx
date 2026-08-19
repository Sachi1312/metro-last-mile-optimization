export function Card({ children, style, ...rest }) {
  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        boxShadow: "var(--shadow)",
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, right }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        marginBottom: 24,
        gap: 16,
        flexWrap: "wrap",
      }}
    >
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.3 }}>{title}</h1>
        {subtitle && (
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{subtitle}</p>
        )}
      </div>
      {right}
    </div>
  );
}

export function StatTile({ label, value, sub, accent }) {
  return (
    <Card style={{ padding: "16px 18px" }}>
      <div style={{ fontSize: 11.5, color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.4 }}>
        {label}
      </div>
      <div
        className="mono"
        style={{ fontSize: 24, fontWeight: 700, marginTop: 6, color: accent || "var(--text-primary)" }}
      >
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>{sub}</div>}
    </Card>
  );
}
