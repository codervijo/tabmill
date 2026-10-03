// Allowlist sanitizer for article HTML rendered in the extension's own print page.
// Parses into an inert document (no script execution, no resource loads) and rebuilds only
// allowed elements/attributes in the target document — never assigns innerHTML.

const ALLOWED = new Set([
  "a", "abbr", "article", "b", "blockquote", "br", "caption", "cite", "code", "dd", "del",
  "details", "dfn", "div", "dl", "dt", "em", "figcaption", "figure", "footer", "h1", "h2", "h3",
  "h4", "h5", "h6", "header", "hr", "i", "img", "ins", "kbd", "li", "main", "mark", "ol", "p",
  "pre", "q", "s", "samp", "section", "small", "span", "strong", "sub", "summary", "sup",
  "table", "tbody", "td", "tfoot", "th", "thead", "time", "tr", "u", "ul", "var",
]);
// Dropped with their content; anything else not allowed is unwrapped (children kept).
const DROP = new Set([
  "script", "style", "noscript", "template", "iframe", "frame", "frameset", "object", "embed",
  "applet", "form", "input", "button", "select", "textarea", "option", "link", "meta", "base",
  "svg", "math", "canvas", "video", "audio", "source", "track", "dialog", "head", "title",
]);
const ATTRS: Record<string, readonly string[]> = {
  a: ["href"],
  img: ["src", "alt", "width", "height"],
  td: ["colspan", "rowspan"],
  th: ["colspan", "rowspan", "scope"],
  ol: ["start", "reversed"],
  time: ["datetime"],
};
const GLOBAL_ATTRS = ["lang", "dir", "title"] as const;
const URL_ATTRS = new Set(["href", "src"]);
const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

export function safeUrl(value: string, base: string): string | null {
  try {
    const url = new URL(value, base);
    return SAFE_PROTOCOLS.has(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function sanitize(html: string, baseUrl: string, target: Document = document): DocumentFragment {
  const inert = new DOMParser().parseFromString(html, "text/html");
  const out = target.createDocumentFragment();
  copyChildren(inert.body, out, target, baseUrl);
  return out;
}

function copyChildren(from: Node, to: Node, doc: Document, base: string): void {
  for (const child of Array.from(from.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) {
      to.appendChild(doc.createTextNode(child.textContent ?? ""));
    } else if (child.nodeType === Node.ELEMENT_NODE) {
      copyElement(child as Element, to, doc, base);
    }
  }
}

function copyElement(el: Element, to: Node, doc: Document, base: string): void {
  const tag = el.tagName.toLowerCase();
  if (DROP.has(tag)) return;
  if (!ALLOWED.has(tag)) {
    copyChildren(el, to, doc, base);
    return;
  }
  const out = doc.createElement(tag);
  for (const name of [...(ATTRS[tag] ?? []), ...GLOBAL_ATTRS]) {
    const value = el.getAttribute(name);
    if (value === null) continue;
    if (URL_ATTRS.has(name)) {
      const safe = safeUrl(value, base);
      if (safe) out.setAttribute(name, safe);
    } else {
      out.setAttribute(name, value);
    }
  }
  if (tag === "a") {
    out.setAttribute("rel", "noopener noreferrer");
    out.setAttribute("target", "_blank");
  }
  copyChildren(el, out, doc, base);
  to.appendChild(out);
}
