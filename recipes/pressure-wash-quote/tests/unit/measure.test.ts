import { describe, expect, it } from "vitest";
import { feetPerPixel, parseScaleLabel, pitchFactor, polygonAreaPx, priceLine } from "../../src/feature/measure";
import { SURFACES } from "../../src/feature/rates";

const driveway = SURFACES.find((s) => s.id === "driveway")!;
const roof = SURFACES.find((s) => s.id === "roof")!;

describe("scale", () => {
  it("parses scale bar labels to feet", () => {
    expect(parseScaleLabel("50 ft")).toBe(50);
    expect(parseScaleLabel("20 m")).toBeCloseTo(65.6168, 3);
    expect(parseScaleLabel("0.2 mi")).toBeCloseTo(1056, 6);
    expect(parseScaleLabel("twenty")).toBeNull();
    expect(parseScaleLabel("0 m")).toBeNull();
  });
  it("calibrates feet per pixel and rejects tiny drags", () => {
    expect(feetPerPixel({ x: 0, y: 0 }, { x: 100, y: 0 }, "50 ft")).toBe(0.5);
    expect(feetPerPixel({ x: 0, y: 0 }, { x: 2, y: 0 }, "50 ft")).toBeNull();
  });
});

describe("area + price", () => {
  it("computes polygon area (shoelace), any winding", () => {
    const square = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
    expect(polygonAreaPx(square)).toBe(100);
    expect(polygonAreaPx([...square].reverse())).toBe(100);
  });
  it("scales area to sq ft and prices with condition", () => {
    const line = priceLine("Driveway 1", driveway, 400, 0.5, { condition: "moderate", rate: 0.22 });
    expect(line.sqft).toBe(100);
    expect(line.total).toBeCloseTo(100 * 0.22 * 1.2, 10);
  });
  it("applies roof pitch only to pitched surfaces", () => {
    expect(pitchFactor(12)).toBeCloseTo(Math.SQRT2, 10);
    const flat = priceLine("Driveway", driveway, 100, 1, { condition: "light", rate: 1, pitch: 12 });
    const pitched = priceLine("Roof", roof, 100, 1, { condition: "light", rate: 1, pitch: 12 });
    expect(flat.sqft).toBe(100);
    expect(pitched.sqft).toBeCloseTo(100 * Math.SQRT2, 10);
  });
});
