# Publishing an extension

How an extension goes from built to live in the Chrome Web Store (CWS), and how updates
ship afterwards. Commands run from the tabmill repo. `tabmill publish` is attended only;
it never runs unattended or in CI.

## 0. One-time: publisher account

- Use a **separate Google account for Lamill**, not a personal one, so no personal identity
  shows on listings. Do this before the first upload: items stay tied to the account that
  created them. Turn on 2-step verification (CWS requires it).
- Register at https://chrome.google.com/webstore/devconsole (one-time registration fee):
  - Publisher name: **Lamill**
  - Contact email: a lamill.io address
  - Verify lamill.io as the publisher domain
- **Trader status (EU DSA):** declared **non-trader** while Lamill earns no money (as of
  2026-10-12; the focus is growing an audience). Switch it in the dashboard *before* any
  monetization (sales, paid tiers, ads where the extensions link). A trader must show EU
  users an address and phone; set up a company first if those mustn't be personal.
- New publishers can publish **2 extensions**; ask for more later. `uv run tabmill status`
  shows the slot count.
- API credentials come from **the Lamill account**:
  `uv run tabmill settings apikeys set CWS_PUBLISHER_ID`, plus `CWS_SA_KEY_FILE`
  (service account) or `CWS_CLIENT_ID` / `CWS_CLIENT_SECRET` / `CWS_REFRESH_TOKEN`.
  Check with `uv run tabmill settings apikeys list` or `uv run tabmill preflight`.

## 1. Prepare the release (tabmill)

1. `uv run tabmill list`: the "needs filling" column must show `—` for the slug.
2. `uv run tabmill release <slug>` runs test → assets → listing draft → release lint →
   zip → slot check → hub export. It never publishes. Fix any `✗` and re-run.
3. Refine the listing draft with the `tabmill-store-listing` skill; check
   `.output/store/` images; `uv run tabmill try <slug>` on real pages.

## 2. Make the lamill.io pages live (before the dashboard)

The CWS form needs a working privacy URL:
`https://lamill.io/extensions/<slug>/privacy`.

1. `tabmill hub` (run by `release`) writes `lamill.io/src/content/extensions.json` with
   status `unlisted`: the pages are live with noindex and hidden from `/extensions` (D-035).
2. In lamill.io: review, commit, and deploy. Tabmill never commits there.
3. Check: `curl -sI https://lamill.io/extensions/<slug>/privacy` → 200.

## 3. First publish (manual; the API can't create items)

In https://chrome.google.com/webstore/devconsole (signed in as Lamill):

1. **Add new item** → upload the release zip that `release` printed.
2. **Store listing:** paste from the listing draft. Category from the recipe's
   `store_category` (Productivity › Tools). Upload icon, screenshots, promo tile from
   `.output/store/`.
3. **Privacy practices:** single-purpose statement, a justification for each permission,
   data-use answers (from the listing draft), privacy URL from step 2.
4. **Distribution:** visibility Public → **Submit for review**.
5. Copy the item ID (in the dashboard URL) into
   `$TABMILL_WORKSPACE/registry.json` → `extensions.<slug>.store_id`.

## 4. During review

`uv run tabmill publish <slug> --check` fetches review status into `registry.json`;
`uv run tabmill status` shows all of them.

## 5. After approval

1. `uv run tabmill hub` → the entry flips to `published` with its store URL. Commit and
   deploy lamill.io.
2. Tool page: re-run `uv run tabmill landing <slug>` for the UTM-tagged store link and
   replace the "coming soon" notice on the portfolio site page (D-033).
3. Once the tool page is live: `uv run tabmill landing <slug> --check`.

## Updates (item already has a `store_id`)

1. Bump `version` in `recipes/<slug>/extension.yaml` and add a `changelog:` entry.
2. `uv run tabmill release <slug>`.
3. `uv run tabmill publish <slug>` (add `--staged` to release manually after approval).
   Runs release lint, asks for confirmation, uploads, submits.
4. `uv run tabmill publish <slug> --check` until approved, then `tabmill hub`.

## Order gotchas

- lamill.io's code must support the status in `extensions.json` before (or in the same
  deploy as) the JSON itself; otherwise the entry disappears and the privacy URL 404s.
- `landing --check` only after the tool page is live.
- Don't push anything while a `‹FILL›` or placeholder remains; `release` blocks on them.
