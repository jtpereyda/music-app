BEGIN;

CREATE TABLE IF NOT EXISTS app.seo_keyword_snapshots (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_date date NOT NULL,
    keyword text NOT NULL
        CHECK (length(btrim(keyword)) > 0),
    target_path text NOT NULL
        CHECK (target_path LIKE '/%'),
    source text NOT NULL
        CHECK (source IN ('google_search_console', 'ahrefs', 'manual')),
    country text NOT NULL DEFAULT 'US',
    device text NOT NULL DEFAULT 'all'
        CHECK (device IN ('all', 'desktop', 'mobile', 'tablet')),
    ranking_url text,
    rank numeric(8, 2)
        CHECK (rank IS NULL OR rank > 0),
    clicks bigint
        CHECK (clicks IS NULL OR clicks >= 0),
    impressions bigint
        CHECK (impressions IS NULL OR impressions >= 0),
    ctr numeric(10, 8)
        CHECK (ctr IS NULL OR (ctr >= 0 AND ctr <= 1)),
    average_position numeric(8, 2)
        CHECK (average_position IS NULL OR average_position > 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    collected_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        snapshot_date,
        keyword,
        target_path,
        source,
        country,
        device
    )
);

CREATE TABLE IF NOT EXISTS app.seo_page_snapshots (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_date date NOT NULL,
    target_path text NOT NULL
        CHECK (target_path LIKE '/%'),
    source text NOT NULL
        CHECK (
            source IN (
                'site_check',
                'google_search_console',
                'google_analytics',
                'ahrefs',
                'manual'
            )
        ),
    http_status smallint
        CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    is_live boolean,
    index_verdict text,
    robots_verdict text,
    user_canonical text,
    google_canonical text,
    last_crawl_time timestamptz,
    organic_sessions bigint
        CHECK (organic_sessions IS NULL OR organic_sessions >= 0),
    organic_users bigint
        CHECK (organic_users IS NULL OR organic_users >= 0),
    key_events numeric(14, 2)
        CHECK (key_events IS NULL OR key_events >= 0),
    referring_domains integer
        CHECK (referring_domains IS NULL OR referring_domains >= 0),
    backlinks integer
        CHECK (backlinks IS NULL OR backlinks >= 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    collected_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date, target_path, source)
);

CREATE TABLE IF NOT EXISTS app.seo_annotations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_date date NOT NULL,
    target_path text
        CHECK (target_path IS NULL OR target_path LIKE '/%'),
    kind text NOT NULL
        CHECK (kind IN ('launch', 'content', 'technical', 'link', 'algorithm', 'note')),
    title text NOT NULL
        CHECK (length(btrim(title)) > 0),
    notes text,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.seo_sync_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source text NOT NULL
        CHECK (
            source IN (
                'site_check',
                'google_search_console',
                'google_analytics',
                'ahrefs',
                'daily'
            )
        ),
    status text NOT NULL
        CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    range_start date,
    range_end date,
    records_written integer NOT NULL DEFAULT 0
        CHECK (records_written >= 0),
    message text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE INDEX IF NOT EXISTS seo_keyword_snapshots_lookup_idx
    ON app.seo_keyword_snapshots (
        keyword,
        target_path,
        source,
        snapshot_date DESC
    );

CREATE INDEX IF NOT EXISTS seo_page_snapshots_lookup_idx
    ON app.seo_page_snapshots (target_path, source, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS seo_annotations_event_idx
    ON app.seo_annotations (event_date DESC, target_path);

CREATE INDEX IF NOT EXISTS seo_sync_runs_started_idx
    ON app.seo_sync_runs (started_at DESC, source);

COMMIT;
