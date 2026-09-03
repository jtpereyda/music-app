# Database

Neon stores operational metadata; it does not replace the canonical MusicXML
under `catalog/scores`.

The initial schema contains:

- a mirror of catalog identities, hymn/art-song content types, score hashes,
  source metadata, and current publication state;
- separate text, translation, tune, and setting rights reviews;
- reproducible render-QA records;
- provider-neutral access grants for future Stripe/manual entitlements; and
- append-only download events suitable for quota enforcement; and
- privacy-light first-party web sessions and public-page views.

Authentication and Stripe webhook ownership are intentionally not baked into
the schema yet. `actor_key` is an opaque server-generated identifier so the
later auth provider can be chosen without migrating every event.

## Apply locally or in CI

Run migrations in filename order, then render and apply the idempotent catalog
seed. For Neon, use a direct, non-pooled connection string for these migration
commands:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0001_initial.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0002_octave_placement.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0003_seo_tracking.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0004_general_score_catalog.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0005_seo_engagement_metrics.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0006_first_party_analytics.sql

python database/scripts/catalog_seed.py \
  | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

Never commit `DATABASE_URL`. Use a pooled Neon connection string for the
serverless application's normal query traffic, and create an isolated Neon
branch with a direct connection for migration and preview tests.

The web app records public-route page views through a same-origin endpoint. A
server-issued, HttpOnly cookie groups views into anonymous 30-minute sessions.
Only pathnames and the entry referrer's hostname are stored; query strings, IP
addresses, and user-agent strings are excluded. Browsers that send DNT or Global
Privacy Control are not tracked.
