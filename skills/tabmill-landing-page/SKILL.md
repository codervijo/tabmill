---
name: tabmill-landing-page
description: Create the SEO tool page that pairs with a Tabmill extension — `tabmill landing <slug>` writes a brief, a Claude session in the portfolio site's repo writes the page from it (with the write-lamill-seo-page skill), and `tabmill landing <slug> --check` records the live URL and resubmits the sitemap. Use when the user asks for a landing page, tool page, SEO page, or "the site side" of an extension, or when hub export skips an extension for lacking a tool_page_url.
---

# Tabmill landing page

D-033: tabmill has no AI and never writes into a site repo. The page is written by a Claude
session opened **in the site repo** (`~/work/projects/sites/<portfolio_site>`).

## Steps

1. **Brief** (tabmill repo): `uv run tabmill landing <slug>` →
   `extensions/<slug>/.output/store/landing-brief.md`. It holds the target URL
   (`https://<portfolio_site>` + recipe `landing_path`, default `/<first keyword>`), queries,
   single purpose, permissions/privacy, the UTM install link (or "Coming soon" before the store
   listing exists), hub + privacy links, and the never-invent rules.
2. **Pick the query with care**: the page must not compete with the site's own core page
   (e.g. markpdf.dev already targets "markdown to pdf"). Set `landing_path` / reorder
   `target_keywords` in the recipe if needed, then regenerate the brief.
3. **Write the page** (site repo): open Claude Code there, attach the brief, "Write the page in
   this brief". That session uses the user-level `write-lamill-seo-page` skill and the site's
   own `AI_AGENTS.md` / `docs/CLAUDE.md` and stack (Astro, Vite + React, …).
4. **Deploy**: the user commits + pushes the site (git-integrated deploy from `main`). Commit
   or push only when the user asks. Don't run `lamill new deploy` for a live site.
5. **Record** (tabmill repo): `uv run tabmill landing <slug> --check` — requires HTTP 200,
   sets `landing_page_url` in the recipe, resubmits the sitemap
   (`lamill settings gsc submit-sitemap --force`; IndexNow skipped, D-016).
6. **Hub**: `uv run tabmill hub` — the extension now exports to lamill.io.

## Done when

Page live (200), in the site's sitemap, recipe has `landing_page_url`, hub entry exported,
store listing and page link to each other.
