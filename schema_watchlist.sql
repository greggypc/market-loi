-- ─────────────────────────────────────────────────────────────────────────────
-- Watchlist Table — run this in Supabase → SQL Editor → New Query → Run
-- Only needed if you are ADDING the watchlist management feature.
-- Your existing snapshots_4am and lois_9am tables are unchanged.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── Watchlist ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlist (
    id         BIGSERIAL PRIMARY KEY,
    symbol     TEXT        NOT NULL UNIQUE,
    sector     TEXT        NOT NULL,
    is_derived BOOLEAN     DEFAULT FALSE,
    active     BOOLEAN     DEFAULT TRUE,
    added_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist (active);
CREATE INDEX IF NOT EXISTS idx_watchlist_sector ON watchlist (sector, symbol);

-- Row Level Security
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_all_watchlist" ON watchlist
    FOR ALL USING (true) WITH CHECK (true);

-- ── Seed with your current 43 tickers ────────────────────────────────────────
INSERT INTO watchlist (symbol, sector, is_derived) VALUES
    -- Indexes
    ('SPY',  'Indexes', FALSE),
    ('QQQ',  'Indexes', FALSE),
    ('SPX',  'Indexes', TRUE),
    ('NDX',  'Indexes', TRUE),
    -- Semiconductors
    ('NVDA', 'Semiconductors', FALSE),
    ('AMD',  'Semiconductors', FALSE),
    ('AVGO', 'Semiconductors', FALSE),
    ('MU',   'Semiconductors', FALSE),
    ('MRVL', 'Semiconductors', FALSE),
    ('INTC', 'Semiconductors', FALSE),
    ('QCOM', 'Semiconductors', FALSE),
    ('TXN',  'Semiconductors', FALSE),
    ('ARM',  'Semiconductors', FALSE),
    ('SNDK', 'Semiconductors', FALSE),
    ('CEVA', 'Semiconductors', FALSE),
    ('WOLF', 'Semiconductors', FALSE),
    ('COHR', 'Semiconductors', FALSE),
    -- Tech / Cloud / AI
    ('MSFT', 'Tech / Cloud / AI', FALSE),
    ('META', 'Tech / Cloud / AI', FALSE),
    ('ORCL', 'Tech / Cloud / AI', FALSE),
    ('IBM',  'Tech / Cloud / AI', FALSE),
    ('NOW',  'Tech / Cloud / AI', FALSE),
    ('PLTR', 'Tech / Cloud / AI', FALSE),
    ('CRWD', 'Tech / Cloud / AI', FALSE),
    ('APP',  'Tech / Cloud / AI', FALSE),
    ('CSCO', 'Tech / Cloud / AI', FALSE),
    ('VRT',  'Tech / Cloud / AI', FALSE),
    ('PENG', 'Tech / Cloud / AI', FALSE),
    ('NBIS', 'Tech / Cloud / AI', FALSE),
    ('CRWV', 'Tech / Cloud / AI', FALSE),
    ('TEM',  'Tech / Cloud / AI', FALSE),
    -- Networking / Comms
    ('APH',  'Networking / Comms', FALSE),
    ('TE',   'Networking / Comms', FALSE),
    ('IREN', 'Networking / Comms', FALSE),
    ('ONDS', 'Networking / Comms', FALSE),
    ('AAOI', 'Networking / Comms', FALSE),
    ('TSSI', 'Networking / Comms', FALSE),
    ('ATXI', 'Networking / Comms', FALSE),
    -- Crypto Mining
    ('MARA', 'Crypto Mining', FALSE),
    ('RIOT', 'Crypto Mining', FALSE),
    ('CLSK', 'Crypto Mining', FALSE),
    -- Aerospace
    ('FLY',  'Aerospace', FALSE),
    -- Clean Energy
    ('ENPH', 'Clean Energy', FALSE)
ON CONFLICT (symbol) DO NOTHING;
