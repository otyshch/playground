-- Initialize PostgreSQL database setup
-- This script runs during database initialization

-- Create the main table (will be done by SQLAlchemy migrations, but here for reference)
-- CREATE TABLE IF NOT EXISTS state_fiscal_data (
--     id SERIAL PRIMARY KEY,
--     state_code CHAR(2) NOT NULL,
--     data_timestamp TIMESTAMP NOT NULL,
--     state_tax_receipts_yoy_growth FLOAT NOT NULL,
--     state_budget_surplus_deficit_as_pct_of_gsp FLOAT NOT NULL,
--     created_at TIMESTAMP DEFAULT NOW(),
--     updated_at TIMESTAMP DEFAULT NOW()
-- );

-- Create indexes (will be created by SQLAlchemy, but here for reference)
-- CREATE INDEX IF NOT EXISTS idx_state_timestamp ON state_fiscal_data (state_code, data_timestamp);
-- CREATE INDEX IF NOT EXISTS idx_data_timestamp ON state_fiscal_data (data_timestamp);

-- Set up database for PostgreSQL optimizations
-- These settings optimize PostgreSQL for time-series workloads
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Note: These settings require a database restart to take effect
-- They are optimized for a typical deployment with 4GB+ RAM