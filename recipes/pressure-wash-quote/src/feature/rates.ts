// Starting rates, copied from washcalc.app `src/rates.js` (MODEL tier) on 2026-10-03.
// WashCalc's own modelling assumptions — not survey data. Shown as editable defaults and
// always labelled "WashCalc model rate"; the user's own rates replace them (stored locally).
export interface Surface {
  id: string;
  label: string;
  /** $ per sq ft, light condition. */
  baseRate: number;
  /** Measured area is the roof's footprint; pitch scales it to true surface area. */
  pitched?: boolean;
}

export const SURFACES: readonly Surface[] = [
  { id: "driveway", label: "Driveway", baseRate: 0.22 },
  { id: "siding", label: "House siding", baseRate: 0.3 },
  { id: "roof", label: "Roof", baseRate: 0.5, pitched: true },
  { id: "deck", label: "Deck", baseRate: 0.38 },
  { id: "patio", label: "Patio", baseRate: 0.25 },
  { id: "fence", label: "Fence", baseRate: 0.32 },
];

export const CONDITIONS = [
  { id: "light", label: "Light", multiplier: 1.0 },
  { id: "moderate", label: "Moderate", multiplier: 1.2 },
  { id: "heavy", label: "Heavy", multiplier: 1.5 },
] as const;

export type ConditionId = (typeof CONDITIONS)[number]["id"];
