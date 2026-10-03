import { describe, expect, it } from "vitest";
import { config } from "../../src/generated/config";

describe("generated funnel config", () => {
  it("tags the CTA and footer links with UTM params", () => {
    for (const url of [config.ctaUrl, config.lamillUrl]) {
      const params = new URL(url).searchParams;
      expect(params.get("utm_source")).toBe(config.slug);
      expect(params.get("utm_medium")).toBe("extension");
      expect(params.get("utm_campaign")).toBeTruthy();
    }
  });

  it("states a single purpose and a privacy line", () => {
    expect(config.singlePurpose.length).toBeGreaterThan(10);
    expect(config.privacy.length).toBeGreaterThan(10);
  });
});
