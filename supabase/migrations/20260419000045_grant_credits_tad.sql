-- Grant 1000 credits to tad@agentics.vn
UPDATE profiles
SET deep_credits_remaining = deep_credits_remaining + 1000
WHERE id = (
  SELECT id FROM auth.users WHERE email = 'tad@agentics.vn'
);
