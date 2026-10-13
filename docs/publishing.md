# Publishing an extension

How an extension goes from built to live in the Chrome Web Store (CWS), and how updates
ship afterwards. Commands run from the tabmill repo. `tabmill ship --publish` is attended
only; it never runs unattended or in CI.

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
  Check with `uv run tabmill settings apikeys list` or `uv run tabmill settings preflight`.

## 1. Prepare the release (tabmill)

1. `uv run tabmill status <slug>`: `next` must not say `fill …`.
2. `uv run tabmill ship <slug>` runs tool-page check → test → assets → listing draft →
   tool-page brief → release lint → zip → slot check → hub export. Without `--publish` it
   never publishes. Fix any `✗` and re-run.
   Everything the dashboard needs lands in one folder:
   `$TABMILL_WORKSPACE/releases/<slug>-<version>/` (zip, icon, screenshots, promo tile,
   listing.md).
3. Refine the listing draft with the `tabmill-store-listing` skill; check
   `.output/store/` images; `uv run tabmill try <slug>` on real pages.

## 2. Make the lamill.io pages live (before the dashboard)

Every extension uses one privacy policy: `https://lamill.io/extensions/privacy` (D-036). Its
source is `tabmill/privacy-policy.yaml`; release lint blocks if the page isn't live, shows an
older `Policy version`, or the extension does more than the policy covers (`privacy-coverage`).

1. If `privacy-coverage` fails: extend `privacy-policy.yaml` only if the policy should really
   promise that, bump `version`, set `updated`.
2. `uv run tabmill advanced hub` → writes `lamill.io/src/content/privacy.json` (always) and
   `extensions.json` (entries with a tool page, as `unlisted` until published — D-035).
3. In lamill.io: review, commit, and deploy. Tabmill never commits there.
4. Check: `curl -s https://lamill.io/extensions/privacy | grep -o 'Policy version [0-9]*'`.
5. Re-run `uv run tabmill ship <slug>`.

## 3. First publish (manual; the API can't create items)

In https://chrome.google.com/webstore/devconsole (signed in as Lamill):

1. **Add new item** → upload the zip from `releases/<slug>-<version>/`.
2. **Store listing:** paste from the listing draft. Category from the recipe's
   `store_category` (Productivity › Tools). Upload icon, screenshots, promo tile from
   the same folder.
3. **Privacy practices:** single-purpose statement, a justification for each permission,
   data-use answers (from the listing draft), privacy URL from step 2.
4. **Distribution:** visibility Public → **Submit for review**.
5. Copy the item ID (in the dashboard URL) into
   `$TABMILL_WORKSPACE/registry.json` → `extensions.<slug>.store_id`.

## 4. During review

`uv run tabmill status <slug> --refresh` fetches review status into `registry.json`;
`uv run tabmill status` shows every extension and its next command.

## 5. After approval

1. `uv run tabmill status <slug> --refresh`, then `uv run tabmill ship <slug>` → the hub entry
   flips to `published` with its store URL, and the tool-page brief gets the UTM-tagged store
   link. Commit and deploy lamill.io.
2. Tool page: replace the "coming soon" notice on the portfolio site page from the new
   brief (D-033).
3. If the tool page wasn't live before: `uv run tabmill ship <slug>` again records it.

## Updates (item already has a `store_id`)

1. Bump `version` in `recipes/<slug>/extension.yaml` and add a `changelog:` entry.
2. `uv run tabmill ship <slug> --publish` (add `--staged` to release manually after
   approval). Runs the release steps, asks for confirmation, uploads, submits.
3. `uv run tabmill status <slug> --refresh` until approved, then `uv run tabmill ship <slug>`
   for the hub.

## Order gotchas

- lamill.io's code must support what `extensions.json` / `privacy.json` contain before (or in
  the same deploy as) the JSON itself; otherwise the entry or the policy page disappears.
- `ship` records the tool page only once it answers HTTP 200; until then it is a `↷`.
- Don't push anything while a `‹FILL›` or placeholder remains; `ship` blocks on them.
