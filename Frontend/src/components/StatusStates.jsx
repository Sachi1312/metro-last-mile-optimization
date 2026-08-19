export function Loading({ label = "Loading data" }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 20px",
        color: "var(--text-secondary)",
        gap: 12,
      }}
    >
      <div
        className="spinner"
        style={{
          width: 26,
          height: 26,
          borderRadius: "50%",
          border: "3px solid var(--border)",
          borderTopColor: "var(--accent)",
          animation: "metroopt-spin 0.8s linear infinite",
        }}
      />
      <div style={{ fontSize: 13 }}>{label}</div>
      <style>{`@keyframes metroopt-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export function ErrorState({ message }) {
  const isNetworkError = !message || /network|fetch|ECONNREFUSED|Failed to fetch/i.test(message);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 20px",
        textAlign: "center",
        gap: 10,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: "50%",
          background: "#FDECEC",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--critical)",
          fontSize: 20,
          fontWeight: 700,
        }}
      >
        !
      </div>
      <div style={{ fontWeight: 600, fontSize: 15 }}>
        {isNetworkError ? "Start the API server first" : "Something went wrong"}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 420 }}>
        {isNetworkError
          ? "The dashboard could not reach the FastAPI backend at http://localhost:8000. Run the server, then refresh this page."
          : message}
      </div>
      {isNetworkError && (
        <code
          className="mono"
          style={{
            marginTop: 6,
            background: "#F4F6F9",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "6px 12px",
            fontSize: 12.5,
          }}
        >
          uvicorn main:app --reload
        </code>
      )}
    </div>
  );
}
