// Estimate print view; the quote came from storage.local and is deleted on read.
import { config } from "@/generated/config";
import { money, sqftText } from "@/feature/measure";
import { isQuote } from "@/feature/quote";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = "", cls = ""): HTMLElementTagNameMap[K] {
  return Object.assign(document.createElement(tag), { textContent: text, className: cls });
}

async function main(): Promise<void> {
  const doc = document.getElementById("doc");
  if (!doc) return;
  const key = decodeURIComponent(location.hash.slice(1));
  const stored = key ? await browser.storage.local.get(key) : {};
  if (key) await browser.storage.local.remove(key);
  const quote: unknown = stored[key];
  if (!isQuote(quote)) {
    doc.append(el("p", "Nothing to print — use “Save estimate as PDF” in the overlay again."));
    return;
  }
  const table = el("table");
  const head = el("tr");
  for (const h of ["Surface", "Condition", "Area", "Rate", "Price"]) head.append(el("th", h));
  table.append(head);
  for (const l of quote.lines) {
    const row = el("tr");
    for (const v of [l.name, l.condition, sqftText(l.sqft), `${money(l.rate)}/sq ft`, money(l.total)]) row.append(el("td", v));
    table.append(row);
  }
  doc.append(
    el("h1", "Pressure washing estimate"),
    el("p", `Prepared ${quote.createdAt} · ${quote.rateNote}`, "meta"),
    table,
    el("p", `Total: ${money(quote.total)}`, "total"),
    el("p", "Areas are measured from satellite imagery and are approximate. Verify on site before quoting.", "meta"),
    el("p", `${config.name} — Built by Lamill`, "meta"),
  );
  document.getElementById("print")?.addEventListener("click", () => window.print());
  window.print();
}

void main();
