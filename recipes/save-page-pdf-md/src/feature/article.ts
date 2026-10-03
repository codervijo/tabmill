/** What the extractor returns from the page (typed across content script → popup → print page). */
export interface Article {
  title: string;
  html: string;
  url: string;
  byline: string | null;
  siteName: string | null;
  lang: string | null;
  /** true when Readability found no article and the whole <body> was used. */
  fallback: boolean;
}

export const HANDOFF_PREFIX = "print:";

export function isArticle(value: unknown): value is Article {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.title === "string" && typeof v.html === "string" && typeof v.url === "string";
}
