-- B.1 checkpoint — product usage events (auth users only).
-- Replaces overloaded `anonymous_usage` for in-app analytics: video screen loads,
-- flop → script CTA clicks, etc. Fire-and-forget inserts from SPA via RLS.

CREATE TABLE usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_usage_events_action_created ON usage_events (action, created_at DESC);
CREATE INDEX idx_usage_events_user_created ON usage_events (user_id, created_at DESC);
CREATE INDEX idx_usage_events_flop_gate ON usage_events (action, created_at DESC)
  WHERE action IN ('video_screen_load', 'flop_cta_click');

ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "usage_events_insert_own"
  ON usage_events FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "usage_events_select_own"
  ON usage_events FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

COMMENT ON TABLE usage_events IS 'B.1+ product analytics: logUsage() from SPA; e.g. video_screen_load, flop_cta_click.';
