/** Estimate handed from the overlay to the print page (session storage, deleted on read). */
export interface QuoteLine {
  name: string;
  surface: string;
  condition: string;
  sqft: number;
  rate: number;
  total: number;
}

export interface Quote {
  createdAt: string;
  lines: QuoteLine[];
  total: number;
  /** "WashCalc model rate" or "your rate", per line set. */
  rateNote: string;
}

export const HANDOFF_PREFIX = "quote:";

export function isQuote(v: unknown): v is Quote {
  if (typeof v !== "object" || v === null) return false;
  const q = v as Record<string, unknown>;
  return Array.isArray(q.lines) && typeof q.total === "number";
}
