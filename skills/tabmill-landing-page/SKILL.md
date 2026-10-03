---
name: tabmill-landing-page
description: Create the SEO landing page that pairs with a Tabmill extension — a web-tool page on the extension's portfolio_site (e.g. markpdf.dev, calcengine.site) targeting the tool query ("markdown to pdf"), linking to the store listing — and get it deployed and indexed via the existing `lamill` CLI. Use when the user asks for a landing page, web page, SEO page, or "the site side" of an extension, or when an extension reaches its landing step.
---

# Tabmill landing page

> DRAFT (v1.A, 2026-10-03). `tabmill landing` is *(planned v1.E)*. Integration facts
> verified 2026-10-03 by reading the `lamill` CLI (`~/work/projects/sites/portfolio`).

## Write surface (policy boundary)

The page lives in the **portfolio site's own repo**: `~/work/projects/sites/<portfolio_site>/`.
That is neither TOOL_DIR nor WORKSPACE_DIR. Tabmill writes only the page (and its link from
the site's nav/hub if the user agrees); site config, build, and deploy belong to that repo
and to `lamill`. Read the site's `AI_AGENTS.md` and `docs/CLAUDE.md` before touching it.

## Steps

1. **Inputs.** From `extensions/<slug>/extension.yaml`: `portfolio_site`, `landing_page_url`,
   `target_keywords`, `single_purpose`, `utm_campaign`; the store URL from `registry.json`
   (`store_id`) — if no store ID yet, the store link is a placeholder and the page must not go live.
2. **Page content.** Invoke the user-level `write-lamill-seo-page` skill. It owns query
   choice, H1/title/slug, metadata, schema, FAQ, internal links. Tabmill-specific inputs:
   - the target query is the **tool** query (e.g. "markdown to pdf"), not "… chrome extension";
   - the page should be useful on its own (a working web tool or a real how-to), with the
     extension as the "do it in one click from any page" option;
   - never invent numbers, ratings, user counts, or reviews.
3. **Stack fit.** Match the site's stack — Astro (`markpdf.dev`, `calcengine.site`), Vite +
   React (`washcalc.app`), TanStack Start (`lamill.io`). Check `lamill.toml [stack]`.
4. **Store link.** `https://chromewebstore.google.com/detail/<store_id>` with
   `utm_source=<portfolio_site>&utm_medium=landing&utm_campaign=<utm_campaign>`.
5. **Build + test** with the site's own Makefile (inside the docker builder: `make build`, `make test`).
6. **Deploy.** Sites deploy git-integrated: a push to the site's `main` triggers the build
   (`lamill.toml [deploy] platform` = `cf-pages` or `vercel`). Commit + push only when the
   user asks. Do **not** run `lamill new deploy` for an already-live site.
7. **Index.**
   - GSC: `lamill settings gsc submit-sitemap --site <portfolio_site> --force` after the deploy is live.
   - IndexNow: **skipped** for landing pages (operator decision D-016, 2026-10-03).
8. **Record.** Set `landing_page_url` in extension.yaml; note the date in `registry.json`.

## Done when

Page live (HTTP 200), in the sitemap, sitemap re-submitted (GSC only), links to the listing with UTM,
listing links back to the page.
