// Pure audit logic: Signals → checks with a status and a fix hint. No DOM access.
import type { Business, Signals } from "./signals";

export type Status = "pass" | "warn" | "fail";

export interface Check {
  id: string;
  label: string;
  status: Status;
  detail: string;
}

/** Digits only; drops a leading US country code so +1 (555) 010-0000 == 555-010-0000. */
export function normalizePhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  return digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits;
}

const norm = (s: string) => s.toLowerCase().replace(/\s+/g, " ").trim();

function schemaCheck(b: Business | undefined, errors: number): Check {
  if (!b) {
    return {
      id: "schema",
      label: "LocalBusiness schema",
      status: "fail",
      detail:
        errors > 0
          ? `${errors} JSON-LD block(s) failed to parse and no LocalBusiness was found — fix the JSON syntax.`
          : "No LocalBusiness JSON-LD found. Add it with name, address, telephone, and opening hours.",
    };
  }
  const missing = [
    ["name", b.name],
    ["telephone", b.telephone],
    ["streetAddress", b.streetAddress],
    ["addressLocality", b.locality],
    ["postalCode", b.postalCode],
  ]
    .filter(([, v]) => !v)
    .map(([k]) => k);
  if (!b.hasOpeningHours) missing.push("openingHours");
  return {
    id: "schema",
    label: `LocalBusiness schema (${b.types.join(", ")})`,
    status: missing.length === 0 ? "pass" : missing.length <= 2 ? "warn" : "fail",
    detail: missing.length === 0 ? "Key fields present." : `Missing: ${missing.join(", ")}.`,
  };
}

function napCheck(b: Business | undefined, s: Signals): Check {
  const label = "NAP consistency (name, address, phone)";
  if (!b) {
    const status: Status = s.phones.length > 0 ? "warn" : "fail";
    return {
      id: "nap",
      label,
      status,
      detail:
        s.phones.length > 0
          ? "Phone found on the page, but no schema to compare against — add LocalBusiness JSON-LD."
          : "No phone number found on the page.",
    };
  }
  const problems: string[] = [];
  if (b.name && !s.text.includes(norm(b.name))) problems.push("business name not in page text");
  if (b.telephone) {
    const want = normalizePhone(b.telephone);
    if (!s.phones.map(normalizePhone).includes(want)) problems.push("schema phone not shown on page");
    const others = new Set(s.phones.map(normalizePhone).filter((p) => p !== want));
    if (others.size > 0) problems.push(`${others.size} other phone number(s) on page`);
  } else if (s.phones.length === 0) {
    problems.push("no phone number anywhere");
  }
  if (b.postalCode && !s.text.includes(norm(b.postalCode))) problems.push("postal code not in page text");
  if (b.streetAddress && !s.text.includes(norm(b.streetAddress))) {
    problems.push("street address not in page text");
  }
  return {
    id: "nap",
    label,
    status: problems.length === 0 ? "pass" : problems.length === 1 ? "warn" : "fail",
    detail: problems.length === 0 ? "Schema NAP matches the page." : `${problems.join("; ")}.`,
  };
}

function locationCheck(b: Business | undefined, s: Signals): Check {
  const served = b?.areaServed.length ?? 0;
  const links = s.locationLinks.length;
  return {
    id: "locations",
    label: "Service-area / location pages",
    status: links > 0 ? "pass" : served > 0 ? "warn" : "fail",
    detail:
      links > 0
        ? `${links} internal location/service-area link(s) found.`
        : served > 0
          ? `Schema lists ${served} served area(s) but no page links to area pages — add one page per area.`
          : "No location or service-area pages linked. Add a page per city or area you serve.",
  };
}

function conversionCheck(s: Signals): Check {
  const found: string[] = [];
  if (s.telLinks > 0) found.push(`${s.telLinks} click-to-call link(s)`);
  if (s.forms > 0) found.push(`${s.forms} form(s)`);
  if (s.ctaTexts.length > 0) found.push(`${s.ctaTexts.length} action button(s)`);
  if (s.hasMapEmbed) found.push("map embed");
  const missing = s.telLinks === 0 ? " Add a tel: click-to-call link." : "";
  return {
    id: "conversion",
    label: "Conversion elements",
    status: found.length >= 2 && s.telLinks > 0 ? "pass" : found.length > 0 ? "warn" : "fail",
    detail: found.length > 0 ? `${found.join(", ")}.${missing}` : "No call, form, or booking action found.",
  };
}

export function audit(s: Signals): Check[] {
  const b = s.businesses[0];
  return [schemaCheck(b, s.jsonLdErrors), napCheck(b, s), locationCheck(b, s), conversionCheck(s)];
}

export function score(checks: Check[]): number {
  const points = { pass: 2, warn: 1, fail: 0 } as const;
  const total = checks.reduce((n, c) => n + points[c.status], 0);
  return Math.round((total / (checks.length * 2)) * 100);
}
