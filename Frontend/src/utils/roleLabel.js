// Human-readable labels for the raw station `role` codes from the station master data.
const ROLE_LABELS = {
  airport: "Airport Terminal",
  airport_adj: "Airport-Adjacent",
  commercial: "Commercial District",
  interchange: "Interchange Station",
  interchange_rail: "Rail Interchange",
  office_heavy: "Office Hub (High Density)",
  office_mid: "Office Hub (Mid Density)",
  office_premium: "Premium Office District",
  office_south: "South Mumbai Office District",
  religious_tourist: "Religious/Tourist Site",
  remote: "Remote/Outlying",
  residential_high: "Residential (High Density)",
  residential_mid: "Residential (Mid Density)",
  shopping_hub: "Shopping Hub",
  terminus_interchange: "Terminus Interchange",
};

export function roleLabel(role) {
  if (!role) return "Station";
  return ROLE_LABELS[role] || role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
