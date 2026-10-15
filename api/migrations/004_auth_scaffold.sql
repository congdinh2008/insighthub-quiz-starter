-- Auth scaffold (learner-r1.3): bảng của Better Auth (web/lib/auth/config.ts), sinh bằng
-- getMigrations của better-auth 1.7.6 rồi review như migration do công cụ sinh.
-- API (FastAPI) chỉ ĐỌC auth_session và auth_user để xác định người dùng (app/core/auth.py).
-- Role insighthub_readonly KHÔNG được cấp quyền trên các bảng này (session token, hash mật khẩu).
CREATE TABLE IF NOT EXISTS auth_user (
    id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    email_verified boolean NOT NULL,
    image text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_session (
    id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL PRIMARY KEY,
    expires_at timestamptz NOT NULL,
    token text NOT NULL UNIQUE,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz NOT NULL,
    ip_address text,
    user_agent text,
    user_id uuid NOT NULL REFERENCES auth_user (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_account (
    id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL PRIMARY KEY,
    account_id text NOT NULL,
    provider_id text NOT NULL,
    user_id uuid NOT NULL REFERENCES auth_user (id) ON DELETE CASCADE,
    access_token text,
    refresh_token text,
    id_token text,
    access_token_expires_at timestamptz,
    refresh_token_expires_at timestamptz,
    scope text,
    password text,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_verification (
    id uuid DEFAULT pg_catalog.gen_random_uuid() NOT NULL PRIMARY KEY,
    identifier text NOT NULL,
    value text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS auth_session_user_id_idx ON auth_session (user_id);
CREATE INDEX IF NOT EXISTS auth_account_user_id_idx ON auth_account (user_id);
CREATE INDEX IF NOT EXISTS auth_verification_identifier_idx ON auth_verification (identifier);
