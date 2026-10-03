import { createContext, useContext, useState } from "react";

const NetworkContext = createContext(null);

export const NETWORKS = [
  { id: "mumbai69", label: "Mumbai — 69 stations" },
  { id: "mumbai_future", label: "Mumbai — future lines" },
  { id: "delhi", label: "Delhi — 50 stations (survey)" },
];

export function NetworkProvider({ children }) {
  const [network, setNetwork] = useState("mumbai69");

  return (
    <NetworkContext.Provider
      value={{
        network,
        setNetwork,
        // Use expansion/file-backed APIs for Delhi and future Mumbai.
        expansion: network !== "mumbai69",
        // Orange synthetic banner only for future Mumbai (no survey).
        synthetic: network === "mumbai_future",
        // Survey-backed LMPI for Mumbai 69 and Delhi.
        surveyBacked: network === "mumbai69" || network === "delhi",
      }}
    >
      {children}
    </NetworkContext.Provider>
  );
}

export function useNetwork() {
  return useContext(NetworkContext);
}
