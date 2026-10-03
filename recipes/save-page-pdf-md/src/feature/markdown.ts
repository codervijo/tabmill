import TurndownService from "turndown";
import type { Article } from "./article";

const service = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
  bulletListMarker: "-",
  emDelimiter: "*",
});
service.remove(["script", "style", "noscript", "iframe", "form", "button", "select", "textarea"]);

/** Markdown document: title, source line, then the article body. */
export function toMarkdown(article: Article, savedOn: Date = new Date()): string {
  const body = service.turndown(article.html).trim();
  const date = savedOn.toISOString().slice(0, 10);
  return `# ${article.title.trim()}\n\n> Source: <${article.url}> · Saved ${date}\n\n${body}\n`;
}
