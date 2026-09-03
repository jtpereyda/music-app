BEGIN;

CREATE TABLE IF NOT EXISTS app.analytics_sessions (
    id uuid PRIMARY KEY,
    landing_path text NOT NULL
        CHECK (
            landing_path LIKE '/%'
            AND length(landing_path) <= 2048
        ),
    referrer_host text
        CHECK (
            referrer_host IS NULL
            OR length(referrer_host) <= 253
        ),
    started_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT analytics_sessions_landing_path_privacy_check
        CHECK (
            strpos(landing_path, '?') = 0
            AND strpos(landing_path, '#') = 0
        ),
    CHECK (last_seen_at >= started_at)
);

CREATE TABLE IF NOT EXISTS app.analytics_page_views (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id uuid NOT NULL
        REFERENCES app.analytics_sessions(id) ON DELETE CASCADE,
    path text NOT NULL
        CHECK (
            path LIKE '/%'
            AND length(path) <= 2048
        ),
    viewed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT analytics_page_views_path_privacy_check
        CHECK (
            strpos(path, '?') = 0
            AND strpos(path, '#') = 0
        )
);

CREATE INDEX IF NOT EXISTS analytics_sessions_last_seen_idx
    ON app.analytics_sessions (last_seen_at DESC);

CREATE INDEX IF NOT EXISTS analytics_page_views_viewed_idx
    ON app.analytics_page_views (viewed_at DESC);

CREATE INDEX IF NOT EXISTS analytics_page_views_session_idx
    ON app.analytics_page_views (session_id, viewed_at DESC);

CREATE INDEX IF NOT EXISTS analytics_page_views_path_viewed_idx
    ON app.analytics_page_views (path, viewed_at DESC);

COMMENT ON TABLE app.analytics_sessions IS
    'Anonymous first-party web sessions. Session IDs expire in the browser after 30 minutes of inactivity.';

COMMENT ON COLUMN app.analytics_sessions.referrer_host IS
    'Hostname-only entry referrer; full referrer URLs and query strings are not stored.';

COMMENT ON TABLE app.analytics_page_views IS
    'First-party public-site page views. Paths exclude query strings and fragments.';

COMMIT;
