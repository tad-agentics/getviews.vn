-- Add niche 24: Crypto / Web3
--
-- Wave 5+ Phase 3 niche expansion. Splits crypto / Web3 / blockchain
-- content away from Tài chính / Đầu tư (niche 15), which currently
-- mixes crypto with traditional finance (stocks, gold, banking,
-- savings). Crypto creators have different format conventions —
-- chart-on-screen TA breakdowns, on-chain reveal explainers, NFT
-- launch reviews — that traditional-finance framing doesn't surface
-- well in niche_intelligence.
--
-- Hashtag strategy: blockchain-specific (DeFi / NFT / Web3 / chains)
-- are niche-defining; broad #crypto and #bitcoin stay shared with
-- niche 15 via ON CONFLICT DO NOTHING (so existing niche-15 mappings
-- aren't overridden). The matcher's array overlap operator will let
-- niche 24 still match those tags, just not preferentially.
--
-- Idempotent: ON CONFLICT DO NOTHING on both tables.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  24,
  'Crypto / Web3',
  'crypto_web3',
  ARRAY[
    -- Web3 / DeFi / NFT subculture (niche-defining)
    '#web3', '#web3vietnam', '#defi', '#defivietnam',
    '#nft', '#nftvietnam', '#nftcommunity', '#nftartist',
    '#dao', '#daovietnam', '#tokenomics', '#airdrop',
    '#airdropvietnam', '#airdrophunter', '#testnetcrypto',
    '#stablecoin', '#yieldfarming', '#staking',
    '#liquiditypool', '#dex', '#cex',
    -- Specific chains + ecosystems
    '#solana', '#sol', '#ethereumvietnam', '#bnb',
    '#polkadot', '#avalanche', '#cosmos', '#layer2',
    '#arbitrum', '#optimism', '#zksync', '#starknet',
    '#aptos', '#sui',
    -- Gaming + metaverse
    '#gamefi', '#axieinfinity', '#stepn',
    '#playtoearn', '#metaverse', '#metaversevietnam',
    -- Trading-specific (chart format markers)
    '#chartcrypto', '#tacrypto', '#tradingsignals',
    '#cryptoanalysis', '#onchain', '#whalealert',
    '#cryptonews', '#cryptonewsvietnam',
    -- Project / tool markers
    '#binancevietnam', '#bybit', '#okx', '#coingecko',
    '#metamask', '#trustwallet', '#hardwarewallet',
    '#ledger', '#coinbase'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 24. ON CONFLICT DO NOTHING leaves
-- generic #crypto / #bitcoin / #ethereum mapped to niche 15 (Finance).
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('web3',                24, 100, 1, 'seed', false),
  ('web3vietnam',         24, 100, 1, 'seed', false),
  ('defi',                24, 100, 1, 'seed', false),
  ('defivietnam',         24, 100, 1, 'seed', false),
  ('nft',                 24, 100, 1, 'seed', false),
  ('nftvietnam',          24, 100, 1, 'seed', false),
  ('nftcommunity',        24, 100, 1, 'seed', false),
  ('nftartist',           24, 100, 1, 'seed', false),
  ('dao',                 24, 100, 1, 'seed', false),
  ('daovietnam',          24, 100, 1, 'seed', false),
  ('tokenomics',          24, 100, 1, 'seed', false),
  ('airdrop',             24, 100, 1, 'seed', false),
  ('airdropvietnam',      24, 100, 1, 'seed', false),
  ('airdrophunter',       24, 100, 1, 'seed', false),
  ('testnetcrypto',       24, 100, 1, 'seed', false),
  ('stablecoin',          24, 100, 1, 'seed', false),
  ('yieldfarming',        24, 100, 1, 'seed', false),
  ('staking',             24, 100, 1, 'seed', false),
  ('liquiditypool',       24, 100, 1, 'seed', false),
  ('dex',                 24, 100, 1, 'seed', false),
  ('cex',                 24, 100, 1, 'seed', false),
  ('solana',              24, 100, 1, 'seed', false),
  ('sol',                 24, 100, 1, 'seed', false),
  ('ethereumvietnam',     24, 100, 1, 'seed', false),
  ('bnb',                 24, 100, 1, 'seed', false),
  ('polkadot',            24, 100, 1, 'seed', false),
  ('avalanche',           24, 100, 1, 'seed', false),
  ('cosmos',              24, 100, 1, 'seed', false),
  ('layer2',              24, 100, 1, 'seed', false),
  ('arbitrum',            24, 100, 1, 'seed', false),
  ('optimism',            24, 100, 1, 'seed', false),
  ('zksync',              24, 100, 1, 'seed', false),
  ('starknet',            24, 100, 1, 'seed', false),
  ('aptos',               24, 100, 1, 'seed', false),
  ('sui',                 24, 100, 1, 'seed', false),
  ('gamefi',              24, 100, 1, 'seed', false),
  ('axieinfinity',        24, 100, 1, 'seed', false),
  ('stepn',               24, 100, 1, 'seed', false),
  ('playtoearn',          24, 100, 1, 'seed', false),
  ('metaverse',           24, 100, 1, 'seed', false),
  ('metaversevietnam',    24, 100, 1, 'seed', false),
  ('chartcrypto',         24, 100, 1, 'seed', false),
  ('tacrypto',            24, 100, 1, 'seed', false),
  ('tradingsignals',      24, 100, 1, 'seed', false),
  ('cryptoanalysis',      24, 100, 1, 'seed', false),
  ('onchain',             24, 100, 1, 'seed', false),
  ('whalealert',          24, 100, 1, 'seed', false),
  ('cryptonews',          24, 100, 1, 'seed', false),
  ('cryptonewsvietnam',   24, 100, 1, 'seed', false),
  ('binancevietnam',      24, 100, 1, 'seed', false),
  ('bybit',               24, 100, 1, 'seed', false),
  ('okx',                 24, 100, 1, 'seed', false),
  ('coingecko',           24, 100, 1, 'seed', false),
  ('metamask',            24, 100, 1, 'seed', false),
  ('trustwallet',         24, 100, 1, 'seed', false),
  ('hardwarewallet',      24, 100, 1, 'seed', false),
  ('ledger',              24, 100, 1, 'seed', false),
  ('coinbase',            24, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
