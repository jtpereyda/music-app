BEGIN;

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.catalog_hymns (
    id text PRIMARY KEY
        CHECK (id ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    catalog_revision integer NOT NULL
        CHECK (catalog_revision > 0),
    title text NOT NULL
        CHECK (length(btrim(title)) > 0),
    score_path text NOT NULL UNIQUE,
    score_sha256 text NOT NULL UNIQUE
        CHECK (score_sha256 ~ '^[0-9a-f]{64}$'),
    score_media_type text NOT NULL,
    original_key_name text NOT NULL,
    original_key_mode text NOT NULL
        CHECK (original_key_mode IN ('major', 'minor')),
    original_key_fifths smallint NOT NULL
        CHECK (original_key_fifths BETWEEN -7 AND 7),
    available_lines text[] NOT NULL
        CHECK (
            cardinality(available_lines) > 0
            AND available_lines <@ ARRAY['SATB', 'S', 'A', 'T', 'B']::text[]
        ),
    lyrics_scope text NOT NULL
        CHECK (lyrics_scope IN ('soprano_only', 'all_lines', 'none')),
    source_rights_status text NOT NULL,
    publication_status text NOT NULL DEFAULT 'technical_preview'
        CHECK (
            publication_status IN (
                'technical_preview',
                'rights_review',
                'approved',
                'rejected',
                'withdrawn'
            )
        ),
    source_collection_id text NOT NULL,
    source_artifact_sha256 text NOT NULL
        CHECK (source_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    source_record_ordinal integer NOT NULL
        CHECK (source_record_ordinal > 0),
    source_x_reference text,
    source_payload jsonb NOT NULL,
    rights_payload jsonb NOT NULL,
    lyrics_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.rights_reviews (
    hymn_id text NOT NULL
        REFERENCES app.catalog_hymns(id) ON DELETE CASCADE,
    component text NOT NULL
        CHECK (component IN ('text', 'translation', 'tune', 'setting')),
    status text NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'public_domain',
                'licensed',
                'rejected',
                'not_applicable'
            )
        ),
    jurisdiction text NOT NULL DEFAULT 'US',
    publication_year smallint,
    evidence jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(evidence) = 'array'),
    review_notes text,
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (hymn_id, component),
    CHECK (
        (status = 'pending' AND reviewed_at IS NULL)
        OR (status <> 'pending' AND reviewed_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS app.render_qa_reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hymn_id text NOT NULL
        REFERENCES app.catalog_hymns(id) ON DELETE CASCADE,
    score_sha256 text NOT NULL
        CHECK (score_sha256 ~ '^[0-9a-f]{64}$'),
    renderer_version text NOT NULL,
    line text NOT NULL
        CHECK (line IN ('satb', 'soprano', 'alto', 'tenor', 'bass')),
    target_key text NOT NULL,
    clef text NOT NULL
        CHECK (clef IN ('original', 'treble', 'bass', 'alto', 'tenor', 'treble-8vb')),
    page_size text NOT NULL
        CHECK (page_size IN ('letter', 'a4')),
    status text NOT NULL
        CHECK (status IN ('pending', 'passed', 'failed')),
    page_count integer
        CHECK (page_count IS NULL OR page_count > 0),
    pdf_sha256 text
        CHECK (pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$'),
    review_notes text,
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        hymn_id,
        score_sha256,
        renderer_version,
        line,
        target_key,
        clef,
        page_size
    )
);

CREATE TABLE IF NOT EXISTS app.access_grants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_key text NOT NULL
        CHECK (length(btrim(actor_key)) > 0),
    source text NOT NULL
        CHECK (source IN ('manual', 'stripe', 'promotion')),
    product_key text NOT NULL,
    status text NOT NULL
        CHECK (status IN ('active', 'expired', 'revoked')),
    external_reference text,
    starts_at timestamptz NOT NULL DEFAULT now(),
    ends_at timestamptz,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE TABLE IF NOT EXISTS app.download_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id uuid NOT NULL UNIQUE,
    actor_key text,
    hymn_id text NOT NULL
        REFERENCES app.catalog_hymns(id),
    target_key text NOT NULL,
    line text NOT NULL
        CHECK (line IN ('satb', 'soprano', 'alto', 'tenor', 'bass')),
    clef text NOT NULL
        CHECK (clef IN ('original', 'treble', 'bass', 'alto', 'tenor', 'treble-8vb')),
    page_size text NOT NULL
        CHECK (page_size IN ('letter', 'a4')),
    outcome text NOT NULL
        CHECK (outcome IN ('started', 'succeeded', 'failed', 'denied')),
    output_bytes bigint
        CHECK (output_bytes IS NULL OR output_bytes >= 0),
    render_duration_ms integer
        CHECK (render_duration_ms IS NULL OR render_duration_ms >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS access_grants_source_reference_uidx
    ON app.access_grants (source, external_reference)
    WHERE external_reference IS NOT NULL;

CREATE INDEX IF NOT EXISTS access_grants_actor_status_idx
    ON app.access_grants (actor_key, status, ends_at DESC);

CREATE INDEX IF NOT EXISTS download_events_actor_created_idx
    ON app.download_events (actor_key, created_at DESC)
    WHERE actor_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS download_events_hymn_created_idx
    ON app.download_events (hymn_id, created_at DESC);

CREATE INDEX IF NOT EXISTS rights_reviews_status_idx
    ON app.rights_reviews (status, hymn_id);

CREATE INDEX IF NOT EXISTS render_qa_reviews_status_idx
    ON app.render_qa_reviews (status, hymn_id);

COMMIT;
