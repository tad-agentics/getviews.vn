-- Merge niche 24 (Crypto / Web3) into niche 15 (Tài chính / Đầu tư).
--
-- Single finance + crypto bucket. Reuses id 15; rebadges niche_id = 24 → 15;
-- merges signal_hashtags; dedupes hashtag_niche_map; resolves UNIQUE conflicts;
-- clears aggregates for 24.
--
-- Post-deploy: SELECT refresh_niche_intelligence(); and let weekly analytics refill.

BEGIN;

-- ── 1. Tài chính / Đầu tư — union id=15 + former id=24 hashtag pools ───────
UPDATE public.niche_taxonomy SET
  signal_hashtags = ARRAY[
    '#taichinh', '#taichinhcanhan', '#tietkiem', '#dautu', '#quanlychitieu',
    '#tietkiemthongminh', '#chungkhoan', '#cophieu', '#quydautu', '#nghihuu',
    '#FIRE', '#financialfreedom', '#richhabits', '#hoachdinhcuocsong', '#taichinhvietnam',
    '#kiemtienthongminh', '#canhbaodautu', '#thitruong', '#laisuatnganhang', '#vangbac',
    '#kinhte',
    '#crypto', '#bitcoin', '#btc', '#ethereum', '#eth',
    '#forex', '#trading', '#tradingcrypto', '#tradingchungkhoan', '#daytrader',
    '#vnindex', '#chungkhoanviet', '#chungkhoanvietnam', '#phantichcophieu', '#phantichkythuat',
    '#etf', '#traiphieu', '#vang', '#vangmieng', '#giavang',
    '#lamgiau', '#tudotaichinh', '#kiemtienonline', '#thunhapphudong', '#thunhapthudong',
    '#budget', '#budgeting', '#savings', '#saving', '#investment',
    '#investing', '#passiveincome', '#moneytips', '#financialliteracy', '#quanlytien',
    '#thetindung', '#vayonline', '#nganhang', '#fintech', '#startup',
    '#taichinh2026', '#dauthilam', '#kienthuctaichinh', '#huongdantaichinh', '#kiemtien',
    '#laisuat2026', '#nhadautu',
    '#web3', '#web3vietnam', '#defi', '#defivietnam',
    '#nft', '#nftvietnam', '#nftcommunity', '#nftartist',
    '#dao', '#daovietnam', '#tokenomics', '#airdrop',
    '#airdropvietnam', '#airdrophunter', '#testnetcrypto',
    '#stablecoin', '#yieldfarming', '#staking',
    '#liquiditypool', '#dex', '#cex',
    '#solana', '#sol', '#ethereumvietnam', '#bnb',
    '#polkadot', '#avalanche', '#cosmos', '#layer2',
    '#arbitrum', '#optimism', '#zksync', '#starknet',
    '#aptos', '#sui',
    '#gamefi', '#axieinfinity', '#stepn',
    '#playtoearn', '#metaverse', '#metaversevietnam',
    '#chartcrypto', '#tacrypto', '#tradingsignals',
    '#cryptoanalysis', '#onchain', '#whalealert',
    '#cryptonews', '#cryptonewsvietnam',
    '#binancevietnam', '#bybit', '#okx', '#coingecko',
    '#metamask', '#trustwallet', '#hardwarewallet',
    '#ledger', '#coinbase'
  ]
WHERE id = 15;

UPDATE public.video_corpus SET niche_id = 15 WHERE niche_id = 24;

DO $$
BEGIN
  IF to_regclass('public.video_shots') IS NOT NULL THEN
    UPDATE public.video_shots SET niche_id = 15 WHERE niche_id = 24;
  END IF;
END $$;

UPDATE public.profiles SET primary_niche = 15 WHERE primary_niche = 24;

UPDATE public.profiles p
SET niche_ids = deduped.new_ids
FROM (
  SELECT
    p2.id,
    (
      SELECT COALESCE(array_agg(val ORDER BY min_idx), '{}')
      FROM (
        SELECT val, min(idx) AS min_idx
        FROM unnest(array_replace(p2.niche_ids, 24, 15)) WITH ORDINALITY AS t(val, idx)
        GROUP BY val
      ) s
    ) AS new_ids
  FROM public.profiles p2
  WHERE p2.niche_ids IS NOT NULL AND 24 = ANY (p2.niche_ids)
) deduped
WHERE p.id = deduped.id;

UPDATE public.chat_sessions SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.hashtag_niche_map
 WHERE niche_id = 24
   AND hashtag IN (SELECT hashtag FROM public.hashtag_niche_map WHERE niche_id = 15);
UPDATE public.hashtag_niche_map SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.trending_sounds
 WHERE niche_id = 24
   AND (sound_id, week_of) IN (
     SELECT sound_id, week_of FROM public.trending_sounds WHERE niche_id = 15
   );
UPDATE public.trending_sounds SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.cross_creator_patterns
 WHERE niche_id = 24
   AND (hook_type, week_of) IN (
     SELECT hook_type, week_of FROM public.cross_creator_patterns WHERE niche_id = 15
   );
UPDATE public.cross_creator_patterns SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.scene_intelligence
 WHERE niche_id = 24
   AND scene_type IN (SELECT scene_type FROM public.scene_intelligence WHERE niche_id = 15);
UPDATE public.scene_intelligence SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.channel_formulas
 WHERE niche_id = 24
   AND handle IN (SELECT handle FROM public.channel_formulas WHERE niche_id = 15);
UPDATE public.channel_formulas SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.niche_daily_sounds
 WHERE niche_id = 24
   AND computed_date IN (
     SELECT computed_date FROM public.niche_daily_sounds WHERE niche_id = 15
   );
UPDATE public.niche_daily_sounds SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.niche_weekly_digest
 WHERE niche_id = 24
   AND week_of IN (SELECT week_of FROM public.niche_weekly_digest WHERE niche_id = 15);
UPDATE public.niche_weekly_digest SET niche_id = 15 WHERE niche_id = 24;

UPDATE public.daily_ritual SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.trending_cards SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.answer_sessions SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.draft_scripts SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.niche_candidates SET assigned_niche_id = 15 WHERE assigned_niche_id = 24;
UPDATE public.trend_velocity SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.format_lifecycle SET niche_id = 15 WHERE niche_id = 24;

UPDATE public.competitor_tracking SET niche_id = 15 WHERE niche_id = 24;
UPDATE public.creator_pattern SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.creator_velocity
 WHERE niche_id = 24
   AND creator_handle IN (SELECT creator_handle FROM public.creator_velocity WHERE niche_id = 15);
UPDATE public.creator_velocity SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.signal_grades
 WHERE niche_id = 24
   AND (hook_type, week_start) IN (
     SELECT hook_type, week_start FROM public.signal_grades WHERE niche_id = 15
   );
UPDATE public.signal_grades SET niche_id = 15 WHERE niche_id = 24;

DELETE FROM public.hook_effectiveness WHERE niche_id = 24;
DELETE FROM public.niche_insights WHERE niche_id = 24;
DELETE FROM public.starter_creators WHERE niche_id = 24;

DELETE FROM public.niche_taxonomy WHERE id = 24;

COMMIT;
