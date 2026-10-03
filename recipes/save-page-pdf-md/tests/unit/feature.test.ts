import { describe, expect, it } from "vitest";
import type { Article } from "../../src/feature/article";
import { isArticle } from "../../src/feature/article";
import { markdownFilename, slugify } from "../../src/feature/filename";
import { toMarkdown } from "../../src/feature/markdown";
import { safeUrl } from "../../src/feature/sanitize";

const article: Article = {
  title: "  Hello, World!  ",
  html: "<h2>Intro</h2><p>Some <strong>bold</strong> text.</p><script>alert(1)</script><pre><code>x = 1</code></pre>",
  url: "https://example.org/post",
  byline: null,
  siteName: null,
  lang: "en",
  fallback: false,
};

describe("filename", () => {
  it("slugifies titles", () => {
    expect(slugify("Crème brûlée: a Guide (2026)")).toBe("creme-brulee-a-guide-2026");
    expect(slugify("!!!")).toBe("page");
    expect(markdownFilename("x".repeat(200))).toBe(`${"x".repeat(80)}.md`);
  });
});

describe("markdown", () => {
  it("writes title, source line, and converted body without scripts", () => {
    const md = toMarkdown(article, new Date("2026-10-03T12:00:00Z"));
    expect(md.startsWith("# Hello, World!\n\n> Source: <https://example.org/post> · Saved 2026-10-03")).toBe(true);
    expect(md).toContain("## Intro");
    expect(md).toContain("**bold**");
    expect(md).toContain("```\nx = 1\n```");
    expect(md).not.toContain("alert");
  });
});

describe("sanitize urls", () => {
  it("keeps http(s)/mailto, resolves relative, drops scripts and data", () => {
    expect(safeUrl("/a", "https://x.dev/p")).toBe("https://x.dev/a");
    expect(safeUrl("mailto:a@b.c", "https://x.dev")).toBe("mailto:a@b.c");
    expect(safeUrl("javascript:alert(1)", "https://x.dev")).toBeNull();
    expect(safeUrl("data:text/html,x", "https://x.dev")).toBeNull();
  });
});

describe("handoff guard", () => {
  it("accepts articles and rejects junk", () => {
    expect(isArticle(article)).toBe(true);
    expect(isArticle({ title: 1 })).toBe(false);
    expect(isArticle(null)).toBe(false);
  });
});
