# Database

Neon stores operational metadata; it does not replace the canonical MusicXML
under `catalog/scores`.

The initial schema contains:

- a mirror of catalog identities, score hashes, source metadata, and current
  publication state;
- separate text, translation, tune, and setting rights reviews;
- reproducible render-QA records;
- provider-neutral access grants for future Stripe/manual entitlements; and
- append-only download events suitable for quota enforcement.

Authentication and Stripe webhook ownership are intentionally not baked into
the schema yet. `actor_key` is an opaque server-generated identifier so the
later auth provider can be chosen without migrating every event.

## Apply locally or in CI

Run migrations in filename order, then render and apply the idempotent catalog
seed:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0001_initial.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f database/migrations/0002_octave_placement.sql

python database/scripts/catalog_seed.py \
  | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

Never commit `DATABASE_URL`. Use a pooled Neon connection string in serverless
deployments and create an isolated Neon branch for migration and preview tests.
