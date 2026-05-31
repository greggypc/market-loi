-- ─────────────────────────────────────────────────────────────────────────────
-- Supabase Schema for Market LOI Dashboard
-- Run this in Supabase → SQL Editor → New Query → Run
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 4AM Bid/Ask Snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS snapshots_4am (
    id          BIGSERIAL PRIMARY KEY,
    snap_date   DATE          NOT NULL,
    snap_ts     TIMESTAMPTZ   NOT NULL,
    symbol      TEXT          NOT NULL,
    sector      TEXT,
    bid         NUMERIC(12,4),
    ask         NUMERIC(12,4),
    spread      NUMERIC(12,4),
    midpoint    NUMERIC(12,4),
    last        NUMERIC(12,4),
    prev_close  NUMERIC(12,4),
    is_derived  BOOLEAN       DEFAULT FALSE,
    note        TEXT,
    UNIQUE (snap_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_snap_date  ON snapshots_4am (snap_date);
CREATE INDEX IF NOT EXISTS idx_snap_sym   ON snapshots_4am (symbol);


-- ── 9AM LOI Records ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lois_9am (
    id           BIGSERIAL PRIMARY KEY,
    snap_date    DATE          NOT NULL,
    snap_ts      TIMESTAMPTZ   NOT NULL,
    symbol       TEXT          NOT NULL,
    sector       TEXT,
    -- Current price
    last         NUMERIC(12,4),
    bid          NUMERIC(12,4),
    ask          NUMERIC(12,4),
    prev_close   NUMERIC(12,4),
    -- Prior day OHLC
    pd_open      NUMERIC(12,4),
    pd_high      NUMERIC(12,4),
    pd_low       NUMERIC(12,4),
    pd_close     NUMERIC(12,4),
    -- Premarket range
    pm_open      NUMERIC(12,4),
    pm_high      NUMERIC(12,4),
    pm_low       NUMERIC(12,4),
    pm_vwap      NUMERIC(12,4),
    pm_mid       NUMERIC(12,4),
    -- Gap analysis
    gap          NUMERIC(12,4),
    gap_pct      NUMERIC(8,3),
    -- Round number levels (comma-separated)
    round_levels TEXT,
    is_derived   BOOLEAN       DEFAULT FALSE,
    note         TEXT,
    UNIQUE (snap_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_loi_date   ON lois_9am (snap_date);
CREATE INDEX IF NOT EXISTS idx_loi_sym    ON lois_9am (symbol);


-- ── Row Level Security (allow your service key full access) ───────────────────
ALTER TABLE snapshots_4am ENABLE ROW LEVEL SECURITY;
ALTER TABLE lois_9am      ENABLE ROW LEVEL SECURITY;

-- Allow service role (your SUPABASE_KEY) to do everything
CREATE POLICY "service_all_snap" ON snapshots_4am
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_all_loi" ON lois_9am
    FOR ALL USING (true) WITH CHECK (true);
