// Approximate fleet-size estimates, derived from each intervention's estimated_cost_lakhs
// divided by an assumed per-vehicle annual operating cost. These are NOT model outputs —
// they're a stated-assumption heuristic on top of the cost figures the optimization pipeline
// already computed, meant to translate "Rs X lakhs" into a physically intuitive vehicle count.
export const ASSUMED_UNIT_COST_LAKHS = {
  auto: 2, // e-rickshaw / auto-rickshaw, ~Rs 2L/vehicle/year (fuel + driver, illustrative)
  bus: 15, // shuttle/BEST bus, ~Rs 15L/vehicle/year (illustrative)
};

// Explicit whitelist rather than loose keyword matching — several intervention names
// mention "bus" or "auto" in passing (e.g. "Covered walkway to nearest bus stop", "Auto
// stand regularization") without actually meaning "deploy a fleet of vehicles", so a
// substring match on those words would misclassify infrastructure/signage interventions
// as fleet deployments.
const AUTO_FLEET_INTERVENTIONS = [
  "deploy pre-positioned auto fleet at peak hours",
  "auto aggregator partnership (ola/uber/rapido)",
  "pre-position auto and e-rickshaw bays at the exit",
  "partner with cab aggregators for guaranteed peak pickup slots",
];
const BUS_FLEET_INTERVENTIONS = [
  "add dedicated best bus feeder route",
  "campus shuttle bus within midc estate",
  "add a feeder bus timed to the peak headway",
];

export function fleetTypeFor(interventionText) {
  const t = (interventionText || "").toLowerCase();
  if (AUTO_FLEET_INTERVENTIONS.some((s) => t.startsWith(s) || t === s)) return "auto";
  if (BUS_FLEET_INTERVENTIONS.some((s) => t.startsWith(s) || t === s)) return "bus";
  return null; // not a fleet-deployment intervention (signage, walkway, frequency, regulation, monitoring)
}

export function estimateFleetCount(interventionText, estimatedCostLakhs) {
  const type = fleetTypeFor(interventionText);
  if (!type || !estimatedCostLakhs) return null;
  const unitCost = ASSUMED_UNIT_COST_LAKHS[type];
  const count = Math.round(estimatedCostLakhs / unitCost);
  return { type, count: Math.max(1, count) };
}

export function fleetLabel(type) {
  if (type === "auto") return "autos/e-rickshaws";
  if (type === "bus") return "buses/shuttles";
  if (type === "cab") return "cab slots";
  return "vehicles";
}

/** Prefer API-provided fleet sizing (expansion); fall back to cost heuristic (Mumbai 69). */
export function resolveFleet(iv) {
  if (iv?.fleet_count && iv?.fleet_type) {
    return { type: iv.fleet_type, count: iv.fleet_count };
  }
  return estimateFleetCount(iv?.intervention, iv?.estimated_cost_lakhs);
}

// Aggregate fleet counts across a list of interventions (each with `intervention` and
// `estimated_cost_lakhs` fields), returning totals per type.
export function aggregateFleetCounts(interventions) {
  const totals = { auto: 0, bus: 0 };
  for (const iv of interventions || []) {
    const est = estimateFleetCount(iv.intervention, iv.estimated_cost_lakhs);
    if (est) totals[est.type] += est.count;
  }
  return totals;
}
