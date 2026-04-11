-- Add own_channel and shot_list to chat_sessions.intent_type CHECK constraint.
-- These intent types were added to the frontend after the original migration was written.

ALTER TABLE chat_sessions
  DROP CONSTRAINT IF EXISTS chat_sessions_intent_type_check;

ALTER TABLE chat_sessions
  ADD CONSTRAINT chat_sessions_intent_type_check CHECK (
    intent_type IS NULL OR intent_type IN (
      'video_diagnosis',
      'content_directions',
      'competitor_profile',
      'own_channel',
      'soi_kenh',
      'brief_generation',
      'trend_spike',
      'find_creators',
      'follow_up',
      'format_lifecycle',
      'shot_list'
    )
  );
