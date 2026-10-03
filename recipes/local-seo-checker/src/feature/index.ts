// local-seo-checker feature: replaces the side-panel template's stub (ADR-0008).
import { runInTab, UserError } from "@/lib/inject";
import { audit, type Check, score } from "./checks";
import "./feature.css";
import { isSignals } from "./signals";

const ICON = { pass: "✓", warn: "↷", fail: "✗" } as const;

function renderChecks(target: HTMLElement, url: string, checks: Check[]): void {
  const heading = Object.assign(document.createElement("p"), {
    className: "ls-score",
    textContent: `Score ${score(checks)}/100 — ${new URL(url).host}`,
  });
  heading.dataset.testid = "score";
  const list = document.createElement("ul");
  list.className = "ls-checks";
  for (const c of checks) {
    const item = document.createElement("li");
    item.className = `ls-${c.status}`;
    item.dataset.check = c.id;
    const title = Object.assign(document.createElement("strong"), { textContent: `${ICON[c.status]} ${c.label}` });
    const detail = Object.assign(document.createElement("span"), { textContent: c.detail });
    item.append(title, detail);
    list.append(item);
  }
  target.replaceChildren(heading, list);
}

export function mount(root: HTMLElement): void {
  const run = Object.assign(document.createElement("button"), { type: "button", textContent: "Audit this page" });
  const results = document.createElement("div");
  results.dataset.testid = "results";
  run.addEventListener("click", async () => {
    run.disabled = true;
    results.textContent = "Reading page…";
    try {
      const signals = await runInTab("/content-scripts/audit.js", isSignals);
      renderChecks(results, signals.url, audit(signals));
    } catch (e) {
      results.textContent = e instanceof UserError ? e.message : "Something went wrong.";
      if (!(e instanceof UserError)) console.error(e);
    } finally {
      run.disabled = false;
    }
  });
  root.append(run, results);
}
