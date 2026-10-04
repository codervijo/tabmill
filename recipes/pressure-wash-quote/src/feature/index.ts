// pressure-wash-quote feature: replaces the maps-overlay template stub (ADR-0008).
// Flow: calibrate on the map's scale bar → trace each surface (click points, double-click or
// Enter to finish) → price per surface → print a PDF estimate. Everything stays in the browser.
import featureCss from "./feature.css?inline";
import { feetPerPixel, money, type Point, polygonAreaPx, priceLine, sqftText, type Line } from "./measure";
import { HANDOFF_PREFIX, type Quote } from "./quote";
import { CONDITIONS, type ConditionId, SURFACES } from "./rates";

interface OverlayContext {
  host: HTMLElement;
  shadow: ShadowRoot;
}

type Mode = { kind: "idle" } | { kind: "calibrate"; points: Point[] } | { kind: "trace"; points: Point[] };

const RATES_KEY = "pwq:rates";

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Record<string, unknown> = {},
  ...kids: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...kids);
  return node;
}

export function mount(root: HTMLElement, ctx?: OverlayContext): void {
  let ftPerPx: number | null = null;
  let mode: Mode = { kind: "idle" };
  const lines: Line[] = [];
  const myRates: Record<string, number> = {};

  // Styles go into whichever root the panel lives in (shadow root on Maps, document in preview).
  const rootNode = root.getRootNode();
  const style = el("style", { textContent: featureCss });
  (rootNode instanceof ShadowRoot ? rootNode : document.head).append(style);
  if (ctx && ctx.shadow !== rootNode) ctx.shadow.append(style.cloneNode(true)); // the drawing layer's root

  // Full-page drawing layer, only interactive while calibrating/tracing (map stays usable otherwise).
  const canvas = el("canvas", { className: "pwq-layer" });
  ctx?.shadow.append(canvas);
  const g = canvas.getContext("2d");

  const status = el("p", { className: "lm-privacy" }, "Step 1: calibrate the scale.");
  status.dataset.testid = "status";
  const scaleInput = el("input", { type: "text", placeholder: "Scale bar label, e.g. 20 m", className: "pwq-input" });
  const calibrate = el("button", { type: "button", textContent: "Calibrate on the scale bar" });
  const surfaceSel = el("select", { className: "pwq-input" }, ...SURFACES.map((s) => el("option", { value: s.id, textContent: s.label })));
  const condSel = el("select", { className: "pwq-input" }, ...CONDITIONS.map((c) => el("option", { value: c.id, textContent: `${c.label} condition` })));
  const pitchInput = el("input", { type: "number", min: "0", max: "24", step: "1", placeholder: "Roof pitch (rise per 12), e.g. 6", className: "pwq-input" });
  const rateInput = el("input", { type: "number", min: "0", step: "0.01", className: "pwq-input" });
  const rateNote = el("span", { className: "pwq-note" });
  const trace = el("button", { type: "button", textContent: "Trace a surface", disabled: true });
  const list = el("ul", { className: "pwq-lines" });
  const total = el("p", { className: "pwq-total" });
  const print = el("button", { type: "button", textContent: "Save estimate as PDF", disabled: true });

  function surface() {
    return SURFACES.find((s) => s.id === surfaceSel.value) ?? SURFACES[0]!;
  }
  function syncRate() {
    const s = surface();
    const mine = myRates[s.id];
    rateInput.value = String(mine ?? s.baseRate);
    rateNote.textContent = mine !== undefined ? "your rate ($/sq ft)" : "WashCalc model rate ($/sq ft) — edit to use yours";
    pitchInput.hidden = !s.pitched;
  }
  surfaceSel.addEventListener("change", syncRate);
  rateInput.addEventListener("change", () => {
    const v = Number(rateInput.value);
    if (v > 0) {
      myRates[surface().id] = v;
      void browser.storage.local.set({ [RATES_KEY]: myRates });
      syncRate();
    }
  });
  void browser.storage.local.get(RATES_KEY).then((stored) => {
    Object.assign(myRates, (stored[RATES_KEY] as Record<string, number> | undefined) ?? {});
    syncRate();
  });

  function resize() {
    canvas.width = innerWidth;
    canvas.height = innerHeight;
    draw();
  }
  function draw() {
    if (!g) return;
    g.clearRect(0, 0, canvas.width, canvas.height);
    if (mode.kind === "idle" || mode.points.length === 0) return;
    g.strokeStyle = mode.kind === "calibrate" ? "#f59e0b" : "#0ea5e9";
    g.fillStyle = "rgba(14,165,233,.18)";
    g.lineWidth = 2;
    g.beginPath();
    mode.points.forEach((p, i) => (i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y)));
    if (mode.kind === "trace" && mode.points.length > 2) g.closePath(), g.fill();
    g.stroke();
    for (const p of mode.points) g.fillRect(p.x - 3, p.y - 3, 6, 6);
  }
  function setMode(next: Mode) {
    mode = next;
    canvas.style.pointerEvents = next.kind === "idle" ? "none" : "auto";
    canvas.style.cursor = next.kind === "idle" ? "default" : "crosshair";
    draw();
  }
  function render() {
    list.replaceChildren(
      ...lines.map((l, i) => {
        const remove = el("button", { type: "button", className: "pwq-x", textContent: "×", title: "Remove" });
        remove.addEventListener("click", () => {
          lines.splice(i, 1);
          render();
        });
        return el("li", {}, el("strong", {}, l.name), ` ${sqftText(l.sqft)} × ${money(l.rate)} → ${money(l.total)}`, remove);
      }),
    );
    const sum = lines.reduce((n, l) => n + l.total, 0);
    total.textContent = lines.length ? `Estimate: ${money(sum)}` : "";
    print.disabled = lines.length === 0;
  }

  function finishTrace() {
    if (mode.kind !== "trace" || mode.points.length < 3 || !ftPerPx) return;
    const s = surface();
    const n = lines.filter((l) => l.surface.id === s.id).length + 1;
    lines.push(
      priceLine(`${s.label} ${n}`, s, polygonAreaPx(mode.points), ftPerPx, {
        condition: condSel.value as ConditionId,
        rate: Number(rateInput.value) || s.baseRate,
        pitch: Number(pitchInput.value) || undefined,
      }),
    );
    setMode({ kind: "idle" });
    status.textContent = "Added. Trace another surface or save the estimate.";
    render();
  }

  canvas.addEventListener("click", (e) => {
    if (mode.kind === "idle") return;
    mode.points.push({ x: e.clientX, y: e.clientY });
    if (mode.kind === "calibrate" && mode.points.length === 2) {
      const [a, b] = mode.points as [Point, Point];
      ftPerPx = feetPerPixel(a, b, scaleInput.value);
      setMode({ kind: "idle" });
      status.textContent = ftPerPx
        ? "Calibrated. Don't zoom the map now. Step 2: pick a surface and trace it."
        : "Couldn't read the scale label — type it like “20 m” or “50 ft”, then calibrate again.";
      trace.disabled = !ftPerPx;
      return;
    }
    draw();
  });
  canvas.addEventListener("dblclick", finishTrace);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Enter") finishTrace();
    if (e.key === "Escape") setMode({ kind: "idle" });
  });
  window.addEventListener("resize", resize);
  resize();

  calibrate.addEventListener("click", () => {
    setMode({ kind: "calibrate", points: [] });
    status.textContent = "Click the left end, then the right end, of the map's scale bar.";
  });
  trace.addEventListener("click", () => {
    setMode({ kind: "trace", points: [] });
    status.textContent = "Click around the surface. Double-click or press Enter to finish; Esc cancels.";
  });
  print.addEventListener("click", async () => {
    const usedOwn = lines.some((l) => myRates[l.surface.id] !== undefined);
    const quote: Quote = {
      createdAt: new Date().toISOString().slice(0, 10),
      lines: lines.map((l) => ({ name: l.name, surface: l.surface.label, condition: l.condition, sqft: l.sqft, rate: l.rate, total: l.total })),
      total: lines.reduce((n, l) => n + l.total, 0),
      rateNote: usedOwn ? "Your rates" : "WashCalc model rates (estimates — not survey data)",
    };
    const key = `${HANDOFF_PREFIX}${crypto.randomUUID()}`;
    await browser.storage.local.set({ [key]: quote });
    await browser.runtime.sendMessage({ type: "tabmill:open-page", path: `/print.html#${key}` });
  });

  root.append(
    el("div", { className: "pwq-step" }, scaleInput, calibrate),
    el("div", { className: "pwq-step" }, surfaceSel, condSel, pitchInput, el("label", { className: "pwq-rate" }, rateInput, rateNote), trace),
    list,
    total,
    print,
    status,
  );
  syncRate();
}
