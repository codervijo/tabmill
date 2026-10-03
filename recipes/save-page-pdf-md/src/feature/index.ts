// save-page-pdf-md feature: replaces the popup template's stub (ADR-0008).
import { type Article, HANDOFF_PREFIX, isArticle } from "./article";
import { runInTab, UserError } from "@/lib/inject";
import { markdownFilename } from "./filename";
import { toMarkdown } from "./markdown";

async function extract(): Promise<Article> {
  const article = await runInTab("/content-scripts/extract.js", isArticle);
  if (!article.html.trim()) throw new UserError("No readable content found on this page.");
  return article;
}

function download(text: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

async function saveMarkdown(): Promise<string> {
  const article = await extract();
  const filename = markdownFilename(article.title);
  download(toMarkdown(article), filename);
  return `Saved ${filename}${article.fallback ? " (whole page — no article found)" : ""}.`;
}

async function savePdf(): Promise<string> {
  const article = await extract();
  const key = `${HANDOFF_PREFIX}${crypto.randomUUID()}`;
  await browser.storage.session.set({ [key]: article });
  await browser.tabs.create({ url: browser.runtime.getURL(`/print.html#${key}`) });
  return "Opened the print view — choose “Save as PDF”.";
}

function button(label: string): HTMLButtonElement {
  return Object.assign(document.createElement("button"), { type: "button", textContent: label });
}

export function mount(root: HTMLElement): void {
  const md = button("Save as Markdown");
  const pdf = button("Save as PDF");
  const status = Object.assign(document.createElement("p"), { className: "lm-privacy" });
  status.setAttribute("role", "status");
  status.dataset.testid = "status";

  const run = (action: () => Promise<string>) => async () => {
    md.disabled = pdf.disabled = true;
    status.textContent = "Reading page…";
    try {
      status.textContent = await action();
    } catch (e) {
      status.textContent = e instanceof UserError ? e.message : "Something went wrong.";
      if (!(e instanceof UserError)) console.error(e);
    } finally {
      md.disabled = pdf.disabled = false;
    }
  };
  md.addEventListener("click", run(saveMarkdown));
  pdf.addEventListener("click", run(savePdf));
  root.append(md, pdf, status);
}
