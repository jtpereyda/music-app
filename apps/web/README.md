# Transposify web MVP

A Next.js 16 App Router frontend for Transposify. The generic music homepage is
served at `/`; the free hymn transposition flow is served at
`/uses/hymn-transposer`. The catalog is intentionally local and static by
default for the MVP.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>.

## SEO admin dashboard

The private keyword dashboard is served at `/admin`. It reads the current
keyword-to-page plan from `../../docs/2026-07-21-keyword-targeting.json`,
including the Ahrefs metrics already captured there.

Create a Google OAuth web client and add these authorized redirect URIs:

```text
http://localhost:3000/api/auth/callback/google
https://transposify.com/api/auth/callback/google
```

Then set `AUTH_SECRET`, `AUTH_GOOGLE_ID`, and `AUTH_GOOGLE_SECRET` in
`.env.local` (or the deployment environment). Generate the secret with
`npx auth secret`. Google sign-in is allowlisted to
`joshua.t.pereyda@gmail.com` in the server-side Auth.js callback, and the
protected layout rechecks that email on every dashboard request.

## Render API contract

Set `RENDER_API_URL` to the render service base URL. The browser
uses a same-origin Next.js proxy so preview failures are handled cleanly and
PDF responses are checked before a download is reported as successful. The
proxy calls the fixed-catalog endpoints:

The root Vercel Services configuration supplies `RENDER_API_URL` through a
private service binding in hosted deployments; set it manually only when
running the two services separately.

```text
GET /v1/hymns/o-for-a-thousand-tongues/preview.svg
    ?key=d-major&line=bass&clef=bass&octave=auto&page_size=letter

GET /v1/hymns/o-for-a-thousand-tongues/score.pdf
    ?key=d-major&line=bass&clef=bass&octave=auto&page_size=letter
```

The generated frontend catalog contains the same 290 stable IDs exposed by the
render service. Without the environment variable, the configurator falls back to a
clearly labeled static layout mock and explains how to connect downloads.

## Neon catalog metadata

The default `CATALOG_SOURCE=static` keeps local builds and deployments
independent of the database. After applying `database/migrations` and the
catalog seed, set `CATALOG_SOURCE=neon` and provide a server-only pooled
`DATABASE_URL`. Database rows must match all canonical score hashes or the
app logs a sanitized warning and uses the immutable static catalog.
