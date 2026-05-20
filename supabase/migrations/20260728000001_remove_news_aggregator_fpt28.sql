-- Sprint 8.5 — block FPT Play sports + 28international news aggregators.
-- Keep in sync with ``creator_blocklist.NEWS_AGGREGATOR_HANDLES``.

BEGIN;

DELETE FROM video_corpus
WHERE LOWER(REGEXP_REPLACE(creator_handle, '^@', '')) IN (
  '28international',
  'fptplay.sports',
  'fptplay.bongdaviet',
  'bongdavadoisong'
);

COMMIT;
