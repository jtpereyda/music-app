BEGIN;

ALTER TABLE app.catalog_hymns
    ADD COLUMN IF NOT EXISTS content_type text NOT NULL DEFAULT 'hymn';

ALTER TABLE app.catalog_hymns
    DROP CONSTRAINT IF EXISTS catalog_hymns_available_lines_check,
    DROP CONSTRAINT IF EXISTS catalog_hymns_lyrics_scope_check,
    DROP CONSTRAINT IF EXISTS catalog_hymns_content_type_check;

ALTER TABLE app.catalog_hymns
    ADD CONSTRAINT catalog_hymns_content_type_check CHECK (
        content_type IN ('hymn', 'art_song')
    ),
    ADD CONSTRAINT catalog_hymns_available_lines_check CHECK (
        cardinality(available_lines) > 0
        AND available_lines
            <@ ARRAY['SCORE', 'SATB', 'S', 'A', 'T', 'B']::text[]
    ),
    ADD CONSTRAINT catalog_hymns_lyrics_scope_check CHECK (
        lyrics_scope IN ('soprano_only', 'vocal_parts', 'all_lines', 'none')
    );

ALTER TABLE app.render_qa_reviews
    DROP CONSTRAINT IF EXISTS render_qa_reviews_line_check;

ALTER TABLE app.render_qa_reviews
    ADD CONSTRAINT render_qa_reviews_line_check CHECK (
        line IN ('score', 'satb', 'soprano', 'alto', 'tenor', 'bass')
    );

ALTER TABLE app.download_events
    DROP CONSTRAINT IF EXISTS download_events_line_check;

ALTER TABLE app.download_events
    ADD CONSTRAINT download_events_line_check CHECK (
        line IN ('score', 'satb', 'soprano', 'alto', 'tenor', 'bass')
    );

COMMIT;
