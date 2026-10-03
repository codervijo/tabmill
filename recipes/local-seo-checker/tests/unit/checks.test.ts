import { describe, expect, it } from "vitest";
import { audit, normalizePhone, score } from "../../src/feature/checks";
import type { Business, Signals } from "../../src/feature/signals";

const biz: Business = {
  types: ["Plumber"],
  name: "Acme Plumbing",
  telephone: "+1 (555) 010-2000",
  streetAddress: "12 Main St",
  locality: "Springfield",
  postalCode: "62701",
  hasOpeningHours: true,
  hasGeo: true,
  areaServed: ["Springfield", "Shelbyville"],
};

function signals(over: Partial<Signals> = {}): Signals {
  return {
    url: "https://acme.test/",
    title: "Acme",
    businesses: [biz],
    jsonLdErrors: 0,
    phones: ["555-010-2000"],
    text: "acme plumbing 12 main st springfield 62701 call 555-010-2000",
    locationLinks: ["/service-areas/springfield"],
    telLinks: 1,
    forms: 1,
    ctaTexts: ["Get a free quote"],
    hasMapEmbed: false,
    ...over,
  };
}

const status = (s: Signals) => Object.fromEntries(audit(s).map((c) => [c.id, c.status]));

describe("normalizePhone", () => {
  it("strips formatting and a US country code", () => {
    expect(normalizePhone("+1 (555) 010-2000")).toBe("5550102000");
    expect(normalizePhone("555.010.2000")).toBe("5550102000");
  });
});

describe("audit", () => {
  it("passes a complete local business page", () => {
    expect(status(signals())).toEqual({ schema: "pass", nap: "pass", locations: "pass", conversion: "pass" });
    expect(score(audit(signals()))).toBe(100);
  });

  it("fails everything on an empty page", () => {
    const s = signals({ businesses: [], phones: [], text: "", locationLinks: [], telLinks: 0, forms: 0, ctaTexts: [] });
    expect(status(s)).toEqual({ schema: "fail", nap: "fail", locations: "fail", conversion: "fail" });
    expect(score(audit(s))).toBe(0);
  });

  it("flags NAP mismatches", () => {
    const s = signals({ phones: ["555-010-2000", "555-999-0000"], text: "acme plumbing call us" });
    const nap = audit(s).find((c) => c.id === "nap");
    expect(nap?.status).toBe("fail");
    expect(nap?.detail).toContain("1 other phone number");
    expect(nap?.detail).toContain("postal code not in page text");
  });

  it("warns on partial schema and reports parse errors", () => {
    const partial = signals({ businesses: [{ ...biz, hasOpeningHours: false }] });
    expect(status(partial).schema).toBe("warn");
    const broken = audit(signals({ businesses: [], jsonLdErrors: 2 })).find((c) => c.id === "schema");
    expect(broken?.detail).toContain("2 JSON-LD block(s) failed to parse");
  });

  it("warns when areas are served but not linked", () => {
    expect(status(signals({ locationLinks: [] })).locations).toBe("warn");
  });

  it("warns on conversion without click-to-call", () => {
    expect(status(signals({ telLinks: 0 })).conversion).toBe("warn");
  });
});
