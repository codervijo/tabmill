# tabmill-release — Chrome Web Store API reference

Verified 2026-10-03 against developer.chrome.com. Re-verify before building `tabmill publish`.

## Version

- **V1 is deprecated and supported only until 2026-10-15.** Build against **V2** only.
  (https://developer.chrome.com/docs/webstore/api/v1, https://developer.chrome.com/blog/cws-api-v2)
- Base URL `https://chromewebstore.googleapis.com`; discovery
  `https://chromewebstore.googleapis.com/$discovery/rest?version=v2`.
- **V2 does not create items** — first upload is via the dashboard "Add new item".
  Visibility (public/unlisted/private) is dashboard-only; publish keeps existing visibility.

## Methods (`name = publishers/{publisherId}/items/{itemId}`)

| Method | Endpoint | Notes |
|---|---|---|
| upload | `POST /upload/v2/{name}:upload` | multipart; returns `uploadState` SUCCEEDED / IN_PROGRESS / FAILED / NOT_FOUND; poll `fetchStatus` if IN_PROGRESS |
| publish | `POST /v2/{name}:publish` | `publishType`: `DEFAULT_PUBLISH` or `STAGED_PUBLISH`; `deployInfos[]`; `skipReview`; `blockOnWarnings` |
| fetchStatus | `GET /v2/{name}:fetchStatus` | per-revision state: PENDING_REVIEW, STAGED, PUBLISHED, PUBLISHED_TO_TESTERS, REJECTED, CANCELLED; takedown / warning flags |
| setPublishedDeployPercentage | `POST /v2/{name}:setPublishedDeployPercentage` | increase-only; items with >10,000 seven-day users only |
| cancelSubmission | `POST /v2/{name}:cancelSubmission` | cancel pending review |

Staged items in the dashboard stay available 30 days, then revert to draft.

## Auth

Scope `https://www.googleapis.com/auth/chromewebstore` (`.readonly` suffices for fetchStatus).

- **Service account (recommended for a CLI):** create one with no roles, add its email in the
  Developer Dashboard → Account. Only one service account per publisher.
  (https://developer.chrome.com/docs/webstore/service-accounts)
- **OAuth client + refresh token:** Web-application client, redirect
  `https://developers.google.com/oauthplayground`, mint refresh token in OAuth Playground.
  UNVERIFIED: refresh tokens for consent screens in "Testing" status may expire after 7 days.

Set with `uv run tabmill settings apikeys set <KEY>` (stored in `tabmill/tabmill.env`, template `tabmill.env.example`): `CWS_PUBLISHER_ID` + either `CWS_SA_KEY_FILE` or
`CWS_CLIENT_ID` / `CWS_CLIENT_SECRET` / `CWS_REFRESH_TOKEN`. Item IDs live per extension in
`registry.json`, not env.

Rate limits: not documented (UNVERIFIED) — see the project's Cloud Console quota page.

## Metrics

No API returns installs / users / impressions. Dashboard-only, exportable as CSV (columns
undocumented — design the importer from a real export). Optional per-item GA4 opt-in gives
listing page views + an `install` event + UTM attribution, 2-month retention.
