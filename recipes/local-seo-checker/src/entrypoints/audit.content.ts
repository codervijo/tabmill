// Injected only on click via scripting.executeScript (activeTab); never registered in the
// manifest. Reads the page, returns raw signals to the side panel; sends nothing anywhere.
import type { Business, Signals } from "@/feature/signals";

const BUSINESS_TYPE = /(LocalBusiness|Store|Restaurant|Dentist|Physician|Attorney|LegalService|Plumber|Electrician|Locksmith|Roofing|HVAC|HomeAndConstruction|ProfessionalService|AutoRepair|AutomotiveBusiness|Salon|Spa|Clinic|MedicalBusiness|RealEstateAgent|FinancialService|FoodEstablishment|LodgingBusiness|SportsActivityLocation|ChildCare|EmergencyService|EntertainmentBusiness|GovernmentOffice|HealthAndBeautyBusiness|InsuranceAgency)/;
const CTA = /\b(book|schedule|get (a )?quote|free (quote|estimate)|estimate|call (now|us|today)|contact us|appointment|request service)\b/i;
const LOCATION = /(service[-_ ]?areas?|areas[-_ ]we[-_ ]serve|locations?|near[-_ ]me|cities|communities)/i;
const PHONE = /(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}\b/g;

type Node = Record<string, unknown>;

function asArray<T>(v: T | T[] | undefined | null): T[] {
  return v === undefined || v === null ? [] : Array.isArray(v) ? v : [v];
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.trim() ? v.trim() : null;
}

function nodes(data: unknown): Node[] {
  return asArray(data as Node | Node[]).flatMap((n) =>
    n && typeof n === "object" ? [n, ...nodes((n as Node)["@graph"])] : [],
  );
}

function toBusiness(n: Node): Business | null {
  const types = asArray(n["@type"] as string | string[]).filter((t) => typeof t === "string");
  if (!types.some((t) => BUSINESS_TYPE.test(t))) return null;
  const address = asArray(n.address as Node | Node[])[0] ?? {};
  const areas = asArray(n.areaServed as unknown).map((a) =>
    typeof a === "string" ? a : str((a as Node)?.name) ?? "",
  );
  return {
    types,
    name: str(n.name),
    telephone: str(n.telephone),
    streetAddress: str(address.streetAddress),
    locality: str(address.addressLocality),
    postalCode: str(address.postalCode),
    hasOpeningHours: Boolean(n.openingHours ?? n.openingHoursSpecification),
    hasGeo: Boolean(n.geo),
    areaServed: areas.filter(Boolean),
  };
}

function visible(el: Element): boolean {
  return (el as HTMLElement).offsetParent !== null || el.getClientRects().length > 0;
}

export default defineContentScript({
  registration: "runtime",
  main(): Signals {
    let jsonLdErrors = 0;
    const businesses: Business[] = [];
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        for (const n of nodes(JSON.parse(s.textContent ?? ""))) {
          const b = toBusiness(n);
          if (b) businesses.push(b);
        }
      } catch {
        jsonLdErrors += 1;
      }
    }
    const rawText = document.body?.innerText ?? "";
    const telAnchors = Array.from(document.querySelectorAll<HTMLAnchorElement>('a[href^="tel:"]'));
    const phones = [
      ...telAnchors.map((a) => a.getAttribute("href")?.slice(4) ?? ""),
      ...(rawText.match(PHONE) ?? []),
    ].filter(Boolean);
    const links = Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"));
    const locationLinks = [
      ...new Set(
        links
          .filter((a) => a.host === location.host && LOCATION.test(`${a.pathname} ${a.textContent ?? ""}`))
          .map((a) => a.pathname),
      ),
    ];
    const ctaTexts = Array.from(document.querySelectorAll("a, button, input[type=submit]"))
      .filter(visible)
      .map((el) => ((el as HTMLInputElement).value || el.textContent || "").trim())
      .filter((t) => t.length < 60 && CTA.test(t));
    return {
      url: location.href,
      title: document.title,
      businesses,
      jsonLdErrors,
      phones,
      text: rawText.toLowerCase().replace(/\s+/g, " "),
      locationLinks,
      telLinks: telAnchors.length,
      forms: Array.from(document.forms).filter((f) => f.querySelector("input, textarea")).length,
      ctaTexts: [...new Set(ctaTexts)],
      hasMapEmbed: Boolean(document.querySelector('iframe[src*="google.com/maps"], iframe[src*="maps.google"]')),
    };
  },
});
