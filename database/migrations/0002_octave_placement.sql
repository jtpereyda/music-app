BEGIN;

ALTER TABLE app.render_qa_reviews
    ADD COLUMN IF NOT EXISTS octave_requested text NOT NULL DEFAULT 'original',
    ADD COLUMN IF NOT EXISTS octave_resolved smallint NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS octave_placement_version smallint NOT NULL DEFAULT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.render_qa_reviews'::regclass
          AND conname = 'render_qa_reviews_octave_requested_check'
    ) THEN
        ALTER TABLE app.render_qa_reviews
            ADD CONSTRAINT render_qa_reviews_octave_requested_check
            CHECK (octave_requested IN ('auto', 'original', 'up', 'down'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.render_qa_reviews'::regclass
          AND conname = 'render_qa_reviews_octave_resolved_check'
    ) THEN
        ALTER TABLE app.render_qa_reviews
            ADD CONSTRAINT render_qa_reviews_octave_resolved_check
            CHECK (octave_resolved BETWEEN -1 AND 1);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.render_qa_reviews'::regclass
          AND conname = 'render_qa_reviews_octave_placement_version_check'
    ) THEN
        ALTER TABLE app.render_qa_reviews
            ADD CONSTRAINT render_qa_reviews_octave_placement_version_check
            CHECK (octave_placement_version > 0);
    END IF;
END
$$;

-- The initial migration used an unnamed UNIQUE constraint. Locate it by its
-- exact ordered column set so this remains safe if PostgreSQL truncated the
-- generated constraint name.
DO $$
DECLARE
    previous_constraint name;
BEGIN
    SELECT constraint_record.conname
    INTO previous_constraint
    FROM (
        SELECT
            constraint_row.conname,
            array_agg(attribute_row.attname ORDER BY key_column.ordinality) AS columns
        FROM pg_constraint AS constraint_row
        CROSS JOIN LATERAL unnest(constraint_row.conkey)
            WITH ORDINALITY AS key_column(attnum, ordinality)
        JOIN pg_attribute AS attribute_row
          ON attribute_row.attrelid = constraint_row.conrelid
         AND attribute_row.attnum = key_column.attnum
        WHERE constraint_row.conrelid = 'app.render_qa_reviews'::regclass
          AND constraint_row.contype = 'u'
        GROUP BY constraint_row.conname
    ) AS constraint_record
    WHERE constraint_record.columns = ARRAY[
        'hymn_id',
        'score_sha256',
        'renderer_version',
        'line',
        'target_key',
        'clef',
        'page_size'
    ]::name[]
    LIMIT 1;

    IF previous_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE app.render_qa_reviews DROP CONSTRAINT %I',
            previous_constraint
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.render_qa_reviews'::regclass
          AND conname = 'render_qa_reviews_render_spec_uq'
    ) THEN
        ALTER TABLE app.render_qa_reviews
            ADD CONSTRAINT render_qa_reviews_render_spec_uq UNIQUE (
                hymn_id,
                score_sha256,
                renderer_version,
                line,
                target_key,
                clef,
                octave_requested,
                octave_placement_version,
                page_size
            );
    END IF;
END
$$;

ALTER TABLE app.download_events
    ADD COLUMN IF NOT EXISTS octave_requested text NOT NULL DEFAULT 'original',
    ADD COLUMN IF NOT EXISTS octave_resolved smallint,
    ADD COLUMN IF NOT EXISTS octave_placement_version smallint NOT NULL DEFAULT 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.download_events'::regclass
          AND conname = 'download_events_octave_requested_check'
    ) THEN
        ALTER TABLE app.download_events
            ADD CONSTRAINT download_events_octave_requested_check
            CHECK (octave_requested IN ('auto', 'original', 'up', 'down'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.download_events'::regclass
          AND conname = 'download_events_octave_resolved_check'
    ) THEN
        ALTER TABLE app.download_events
            ADD CONSTRAINT download_events_octave_resolved_check
            CHECK (
                octave_resolved IS NULL
                OR octave_resolved BETWEEN -1 AND 1
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'app.download_events'::regclass
          AND conname = 'download_events_octave_placement_version_check'
    ) THEN
        ALTER TABLE app.download_events
            ADD CONSTRAINT download_events_octave_placement_version_check
            CHECK (octave_placement_version > 0);
    END IF;
END
$$;

COMMIT;
