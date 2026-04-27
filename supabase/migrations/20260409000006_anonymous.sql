-- anonymous_usage — IP-hashed free Soi Kênh (service_role only)

CREATE TABLE IF NOT EXISTS anonymous_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip_hash TEXT NOT NULL UNIQUE,
  has_used_free_soikenh BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE anonymous_usage ENABLE ROW LEVEL SECURITY;
