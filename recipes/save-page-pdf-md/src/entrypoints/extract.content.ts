// Injected only on click via scripting.executeScript (activeTab); never registered in the
// manifest. Runs Readability on a clone so the live page is untouched; nothing leaves the
// browser — the result goes back to the popup.
import { Readability } from "@mozilla/readability";
import type { Article } from "@/feature/article";

export default defineContentScript({
  registration: "runtime",
  main(): Article {
    const base = { url: location.href, lang: document.documentElement.lang || null };
    const parsed = new Readability(document.cloneNode(true) as Document).parse();
    if (parsed?.content) {
      return {
        ...base,
        title: parsed.title || document.title,
        html: parsed.content,
        byline: parsed.byline ?? null,
        siteName: parsed.siteName ?? null,
        fallback: false,
      };
    }
    return {
      ...base,
      title: document.title,
      html: document.body?.innerHTML ?? "",
      byline: null,
      siteName: null,
      fallback: true,
    };
  },
});
