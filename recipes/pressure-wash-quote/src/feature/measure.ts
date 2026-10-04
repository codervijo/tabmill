// Pure measurement + pricing math (unit-tested). No DOM, no network.
import { CONDITIONS, type ConditionId, type Surface } from "./rates";

export interface Point {
  x: number;
  y: number;
}

const FEET_PER: Record<string, number> = {
  ft: 1, feet: 1, foot: 1, m: 3.28084, meter: 3.28084, meters: 3.28084,
  km: 3280.84, mi: 5280, mile: 5280, miles: 5280, yd: 3, yards: 3,
};

/** "20 m", "50 ft", "0.2 mi" → feet. null if unreadable. */
export function parseScaleLabel(label: string): number | null {
  const m = label.trim().toLowerCase().replace(",", ".").match(/^(\d+(?:\.\d+)?)\s*([a-z]+)$/);
  if (!m) return null;
  const per = FEET_PER[m[2] ?? ""];
  const value = Number(m[1]);
  return per && value > 0 ? value * per : null;
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/** Calibration: the user clicked both ends of the map's scale bar and typed its label. */
export function feetPerPixel(a: Point, b: Point, label: string): number | null {
  const feet = parseScaleLabel(label);
  const px = distance(a, b);
  return feet && px >= 5 ? feet / px : null;
}

/** Shoelace formula, square pixels. */
export function polygonAreaPx(points: Point[]): number {
  let sum = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    if (a && b) sum += a.x * b.y - b.x * a.y;
  }
  return Math.abs(sum) / 2;
}

/** Roof surface ÷ footprint for a rise-over-12 pitch (e.g. 6 → 6/12 ≈ 1.118). */
export function pitchFactor(risePer12: number): number {
  return Math.sqrt(1 + (risePer12 / 12) ** 2);
}

export interface Line {
  name: string;
  surface: Surface;
  condition: ConditionId;
  sqft: number;
  rate: number;
  total: number;
}

export function priceLine(
  name: string,
  surface: Surface,
  areaPx: number,
  ftPerPx: number,
  opts: { condition: ConditionId; rate: number; pitch?: number },
): Line {
  const footprint = areaPx * ftPerPx ** 2;
  const sqft = surface.pitched && opts.pitch ? footprint * pitchFactor(opts.pitch) : footprint;
  const multiplier = CONDITIONS.find((c) => c.id === opts.condition)?.multiplier ?? 1;
  return { name, surface, condition: opts.condition, sqft, rate: opts.rate, total: sqft * opts.rate * multiplier };
}

export const money = (n: number) => `$${n.toFixed(2)}`;
export const sqftText = (n: number) => `${Math.round(n).toLocaleString("en-US")} sq ft`;
