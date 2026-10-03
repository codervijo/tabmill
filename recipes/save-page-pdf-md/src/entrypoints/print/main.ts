// Extension-owned print page: renders the handed-off article with MarkPDF-style typography
// and opens the print dialog. The article came from session storage and is deleted on read.
import { isArticle } from "@/feature/article";
import { sanitize } from "@/feature/sanitize";

const IMAGE_WAIT_MS = 3000;

function imagesSettled(root: HTMLElement): Promise<void> {
  const pending = Array.from(root.querySelectorAll("img")).filter((img) => !img.complete);
  const loads = pending.map(
    (img) =>
      new Promise<void>((done) => {
        img.addEventListener("load", () => done(), { once: true });
        img.addEventListener("error", () => done(), { once: true });
      }),
  );
  const timeout = new Promise<void>((done) => setTimeout(done, IMAGE_WAIT_MS));
  return Promise.race([Promise.all(loads).then(() => undefined), timeout]);
}

function meta(text: string): HTMLParagraphElement {
  return Object.assign(document.createElement("p"), { className: "doc-meta", textContent: text });
}

async function main(): Promise<void> {
  const doc = document.getElementById("doc");
  if (!doc) return;
  const key = decodeURIComponent(location.hash.slice(1));
  const stored = key ? await browser.storage.session.get(key) : {};
  if (key) await browser.storage.session.remove(key);
  const article: unknown = stored[key];
  if (!isArticle(article)) {
    doc.append(meta("Nothing to print — use “Save as PDF” from the toolbar button again."));
    return;
  }
  document.title = article.title; // Chrome uses this as the default PDF file name.
  if (article.lang) document.documentElement.lang = article.lang;
  const h1 = Object.assign(document.createElement("h1"), { textContent: article.title });
  const source = [article.siteName, article.byline].filter(Boolean).join(" · ");
  doc.append(h1, meta(`${source ? `${source} — ` : ""}${article.url}`));
  doc.append(sanitize(article.html, article.url));
  document.getElementById("print")?.addEventListener("click", () => window.print());
  await imagesSettled(doc);
  window.print();
}

void main();
