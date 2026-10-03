import axios from "axios";

export const API_BASE = "http://localhost:8420";

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

export const api = {
  health: () => client.get("/"),
  networkSummary: () => client.get("/network/summary"),
  stations: (line) => client.get("/stations", { params: line ? { line } : {} }),
  station: (name) => client.get(`/station/${encodeURIComponent(name)}`),
  forecast30: (name) => client.get(`/forecast/${encodeURIComponent(name)}`),
  forecast2026: (name, month) =>
    client.get(`/forecast/2026/${encodeURIComponent(name)}`, {
      params: month ? { month } : {},
    }),
  interventions: (severity, limit = 20) =>
    client.get("/interventions", { params: { severity, limit } }),
  frequency: (name) => client.get(`/frequency/${encodeURIComponent(name)}`),
  interchange: (eventType) =>
    client.get("/interchange", { params: eventType ? { event_type: eventType } : {} }),
  lineStations: (line) => client.get(`/lmpi/line/${encodeURIComponent(line)}`),
  historical: (name, year, month) =>
    client.get(`/historical/${encodeURIComponent(name)}`, {
      params: year && month ? { year, month } : {},
    }),
  classificationDetails: () => client.get("/classification/details"),
  modelComparison: () => client.get("/models/comparison"),
  festivals: () => client.get("/festivals"),
  festivalImpact: (festivalName) => client.get(`/festivals/${encodeURIComponent(festivalName)}`),
  expansionNetworks: () => client.get("/expansion/networks"),
  expansionStations: (network) => client.get("/expansion/stations", { params: { network } }),
  expansionStation: (name, network) =>
    client.get(`/expansion/station/${encodeURIComponent(name)}`, { params: { network } }),
  expansionFestivals: (network) => client.get("/expansion/festivals", { params: { network } }),
  expansionFestivalImpact: (name, network) =>
    client.get(`/expansion/festivals/${encodeURIComponent(name)}`, { params: { network } }),
  expansionForecast: (name, network) =>
    client.get(`/expansion/forecast/${encodeURIComponent(name)}`, { params: { network } }),
  expansionInterventions: (network) => client.get("/expansion/interventions", { params: { network } }),
  expansionInterchange: (network) => client.get("/expansion/interchange", { params: { network } }),
  expansionEvaluation: () => client.get("/expansion/evaluation"),
  expansionChoice: (network, stationName) =>
    client.get("/expansion/choice", { params: { network, station_name: stationName || undefined } }),
  expansionFutureImpact: () => client.get("/expansion/future-impact"),
  expansionClassification: (network) => client.get("/expansion/classification", { params: { network } }),
};

export default api;
