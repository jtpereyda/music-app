BEGIN;

ALTER TABLE app.seo_page_snapshots
    ADD COLUMN IF NOT EXISTS engaged_sessions bigint
        CHECK (engaged_sessions IS NULL OR engaged_sessions >= 0),
    ADD COLUMN IF NOT EXISTS engagement_duration_seconds numeric(16, 3)
        CHECK (
            engagement_duration_seconds IS NULL
            OR engagement_duration_seconds >= 0
        );

COMMENT ON COLUMN app.seo_page_snapshots.engaged_sessions IS
    'Daily GA4 engaged sessions for the page and acquisition segment.';

COMMENT ON COLUMN app.seo_page_snapshots.engagement_duration_seconds IS
    'Daily GA4 foreground engagement time in seconds for the page and acquisition segment.';

COMMIT;
