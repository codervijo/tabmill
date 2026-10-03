/** Raw facts the audit script reads from the page (typed content script → side panel). */
export interface Business {
  types: string[];
  name: string | null;
  telephone: string | null;
  streetAddress: string | null;
  locality: string | null;
  postalCode: string | null;
  hasOpeningHours: boolean;
  hasGeo: boolean;
  areaServed: string[];
}

export interface Signals {
  url: string;
  title: string;
  /** LocalBusiness-like JSON-LD nodes found on the page. */
  businesses: Business[];
  /** JSON-LD blocks that failed to parse. */
  jsonLdErrors: number;
  /** Phone numbers in tel: links and visible text, digits only. */
  phones: string[];
  /** Visible page text, lowercased and whitespace-collapsed (for NAP matching). */
  text: string;
  /** Internal links that look like location / service-area pages. */
  locationLinks: string[];
  telLinks: number;
  forms: number;
  /** Visible buttons/links whose text reads like a conversion action. */
  ctaTexts: string[];
  hasMapEmbed: boolean;
}

export function isSignals(v: unknown): v is Signals {
  if (typeof v !== "object" || v === null) return false;
  const s = v as Record<string, unknown>;
  return typeof s.url === "string" && Array.isArray(s.businesses) && typeof s.text === "string";
}
