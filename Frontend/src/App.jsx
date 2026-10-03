import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import NetworkMap from "./pages/NetworkMap.jsx";
import StationDetail from "./pages/StationDetail.jsx";
import Classification from "./pages/Classification.jsx";
import Forecasting from "./pages/Forecasting.jsx";
import Interventions from "./pages/Interventions.jsx";
import InterchangeSync from "./pages/InterchangeSync.jsx";
import FestivalImpact from "./pages/FestivalImpact.jsx";
import ModelComparison from "./pages/ModelComparison.jsx";
import FutureImpact from "./pages/FutureImpact.jsx";
import { NetworkProvider } from "./context/NetworkContext.jsx";

function Footer() {
  return (
    <footer
      style={{
        padding: "18px 32px",
        borderTop: "1px solid var(--border)",
        fontSize: 12,
        color: "var(--text-secondary)",
        textAlign: "center",
      }}
    >
      MetroOpt — Mumbai Metro Resource Optimization | Group 7 | K.J. Somaiya School of Engineering
    </footer>
  );
}

export default function App() {
  return (
    <NetworkProvider>
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <main style={{ flex: 1, padding: "28px 32px", overflowX: "auto" }}>
          <Routes>
            <Route path="/" element={<NetworkMap />} />
            <Route path="/station" element={<StationDetail />} />
            <Route path="/station/:name" element={<StationDetail />} />
            <Route path="/classification" element={<Classification />} />
            <Route path="/forecasting" element={<Forecasting />} />
            <Route path="/interventions" element={<Interventions />} />
            <Route path="/interchange" element={<InterchangeSync />} />
            <Route path="/festivals" element={<FestivalImpact />} />
            <Route path="/future-impact" element={<FutureImpact />} />
            <Route path="/models" element={<ModelComparison />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </div>
    </NetworkProvider>
  );
}
