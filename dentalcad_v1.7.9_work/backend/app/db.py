import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL manquant")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(256) UNIQUE NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    full_name VARCHAR(256) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'readonly',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    case_number VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(256),
    status VARCHAR(32) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS implants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    system_id VARCHAR(64),
    diameter_mm NUMERIC(4,2),
    length_mm NUMERIC(4,2),
    position_x NUMERIC(8,3),
    position_y NUMERIC(8,3),
    position_z NUMERIC(8,3),
    axis_x NUMERIC(9,6),
    axis_y NUMERIC(9,6),
    axis_z NUMERIC(9,6),
    tooth_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ajouts v1.3 (compatibles avec une base existante)
ALTER TABLE patients ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);
ALTER TABLE cases    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id);
ALTER TABLE implants ADD COLUMN IF NOT EXISTS plan_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE implants ADD COLUMN IF NOT EXISTS axis_x NUMERIC(9,6);
ALTER TABLE implants ADD COLUMN IF NOT EXISTS axis_y NUMERIC(9,6);
ALTER TABLE implants ADD COLUMN IF NOT EXISTS axis_z NUMERIC(9,6);
ALTER TABLE implants ADD COLUMN IF NOT EXISTS tooth_json JSONB;

CREATE TABLE IF NOT EXISTS plan_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    plan_sha256 VARCHAR(64) NOT NULL,
    canonical_plan JSONB,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMPTZ,
    UNIQUE (case_id, version)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description VARCHAR(256) NOT NULL
);
INSERT INTO schema_version (version, description) VALUES (2, 'canonical plan, implant axes/tooth and upload hardening') ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,
    action VARCHAR(64) NOT NULL,
    target VARCHAR(256),
    details TEXT,
    ip VARCHAR(64)
);
"""

def init_db():
    with engine.connect() as conn:
        conn.exec_driver_sql(SCHEMA)
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
