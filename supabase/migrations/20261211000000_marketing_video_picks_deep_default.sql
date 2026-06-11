-- Marketing corpus pick: default analysis depth → deep (basic mode removed from product).

ALTER TABLE public.marketing_video_picks
  ALTER COLUMN analysis_depth SET DEFAULT 'deep';

CREATE OR REPLACE FUNCTION public.record_marketing_video_pick(
  p_video_id TEXT,
  p_creator_niche_id INT,
  p_priority_weight SMALLINT,
  p_analysis_depth TEXT DEFAULT 'deep'
)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_picked_at TIMESTAMPTZ;
BEGIN
  IF p_analysis_depth NOT IN ('basic', 'deep') THEN
    RAISE EXCEPTION 'invalid_analysis_depth';
  END IF;

  INSERT INTO public.marketing_video_picks (
    video_id,
    creator_niche_id,
    priority_weight,
    analysis_depth
  )
  VALUES (
    p_video_id,
    p_creator_niche_id,
    p_priority_weight,
    p_analysis_depth
  )
  ON CONFLICT (video_id) DO NOTHING
  RETURNING picked_at INTO v_picked_at;

  IF v_picked_at IS NULL THEN
    SELECT picked_at INTO v_picked_at
    FROM public.marketing_video_picks
    WHERE video_id = p_video_id;
  END IF;

  RETURN v_picked_at;
END;
$$;
