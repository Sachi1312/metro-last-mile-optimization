export default function SyntheticBanner({ children }) {
  return (
    <div
      style={{
        padding: "12px 16px",
        background: "#FFF8E8",
        border: "1px solid #EF9F27",
        borderRadius: 8,
        fontSize: 12.5,
        lineHeight: 1.55,
        marginBottom: 18,
      }}
    >
      <strong>Synthetic scenario. </strong>
      {children}
    </div>
  );
}
