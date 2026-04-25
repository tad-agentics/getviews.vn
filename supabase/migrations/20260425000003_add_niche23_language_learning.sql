-- Add niche 23: Học tiếng (Language Learning)
--
-- Wave 5+ Phase 3 niche expansion. Splits language-learning content
-- away from EduTok (niche 11), which currently mixes language tutorials
-- with general academics, exam prep, soft skills, and book reviews.
-- Language-learning is a clear creator subculture (IELTS prep
-- instructors, native-speaker explainers, polyglot vloggers) with
-- distinct format conventions (vocabulary-card lessons, conversation
-- breakdowns, comparative-grammar shorts) that the broader EduTok
-- bucket can't surface in niche_intelligence.
--
-- Hashtag strategy: niche-defining tags only (proficiency tests,
-- target-language pairs, classroom format markers). Generic
-- #hoctienganh is intentionally NOT moved from niche 11 — kept as a
-- shared signal so EduTok still surfaces general-English content.
-- The hashtag_niche_map seeds use ON CONFLICT DO NOTHING so any tag
-- already mapped to niche 11 stays there.
--
-- classify_format: lesson-bucket gate extended to include niche_id 23
-- in a paired corpus_ingest.py change in the same PR — language
-- lessons are the canonical lesson-format inhabitant.
--
-- Idempotent: ON CONFLICT DO NOTHING on both tables.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  23,
  'Học tiếng (Ngoại ngữ)',
  'language_learning',
  ARRAY[
    -- Proficiency-test markers (strong language-learning signals)
    '#ielts7', '#ielts8', '#ielts9', '#bandscore',
    '#toeic800', '#toeic900', '#cefr', '#cefrb1',
    '#cefrb2', '#cefrc1', '#jlpt', '#jlptn3',
    '#jlptn2', '#jlptn1', '#topik', '#hsk',
    '#hsk4', '#hsk5', '#hsk6', '#delf',
    '#dele', '#cambridgeenglish',
    -- Skill format markers
    '#pronunciation', '#phatamtienganh', '#phatam',
    '#tudienenglish', '#vocabularybuilder', '#wordoftheday',
    '#tuvungmoi', '#hoctuvung', '#nguphap',
    '#ngupháptienganh', '#tu_vung_tieng_anh', '#englishidioms',
    '#idiomofday', '#englishphrases', '#cumtu',
    '#shadowing', '#luyennoi', '#luyennghe',
    '#englishlistening', '#englishspeaking',
    -- Target-language pairs
    '#hoctienghan_chonguoimoibatdau', '#tienghancoban',
    '#hoctiengnhat_jlpt', '#tiengnhatcoban',
    '#hoctiengtrung_chonguoimoibatdau', '#tiengtrungcoban',
    '#hoctiengphap_coban', '#hoctiengduc',
    '#hoctiengtaybanha',
    -- Genre/personality markers
    '#polyglot', '#langtok', '#languagetok',
    '#englishteacher', '#nativetutor', '#langlearner',
    '#duolingostreak', '#tienganhgiaotiep',
    '#tienganhcongviec', '#englishforwork',
    '#englishforbusiness', '#englishforchildren'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 23. ON CONFLICT DO NOTHING preserves
-- existing niche 11 mappings for any already-mapped tags.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('ielts7',                         23, 100, 1, 'seed', false),
  ('ielts8',                         23, 100, 1, 'seed', false),
  ('ielts9',                         23, 100, 1, 'seed', false),
  ('bandscore',                      23, 100, 1, 'seed', false),
  ('toeic800',                       23, 100, 1, 'seed', false),
  ('toeic900',                       23, 100, 1, 'seed', false),
  ('cefr',                           23, 100, 1, 'seed', false),
  ('cefrb1',                         23, 100, 1, 'seed', false),
  ('cefrb2',                         23, 100, 1, 'seed', false),
  ('cefrc1',                         23, 100, 1, 'seed', false),
  ('jlpt',                           23, 100, 1, 'seed', false),
  ('jlptn3',                         23, 100, 1, 'seed', false),
  ('jlptn2',                         23, 100, 1, 'seed', false),
  ('jlptn1',                         23, 100, 1, 'seed', false),
  ('topik',                          23, 100, 1, 'seed', false),
  ('hsk',                            23, 100, 1, 'seed', false),
  ('hsk4',                           23, 100, 1, 'seed', false),
  ('hsk5',                           23, 100, 1, 'seed', false),
  ('hsk6',                           23, 100, 1, 'seed', false),
  ('delf',                           23, 100, 1, 'seed', false),
  ('dele',                           23, 100, 1, 'seed', false),
  ('cambridgeenglish',               23, 100, 1, 'seed', false),
  ('pronunciation',                  23, 100, 1, 'seed', false),
  ('phatamtienganh',                 23, 100, 1, 'seed', false),
  ('phatam',                         23, 100, 1, 'seed', false),
  ('tudienenglish',                  23, 100, 1, 'seed', false),
  ('vocabularybuilder',              23, 100, 1, 'seed', false),
  ('wordoftheday',                   23, 100, 1, 'seed', false),
  ('tuvungmoi',                      23, 100, 1, 'seed', false),
  ('hoctuvung',                      23, 100, 1, 'seed', false),
  ('nguphap',                        23, 100, 1, 'seed', false),
  ('englishidioms',                  23, 100, 1, 'seed', false),
  ('idiomofday',                     23, 100, 1, 'seed', false),
  ('englishphrases',                 23, 100, 1, 'seed', false),
  ('cumtu',                          23, 100, 1, 'seed', false),
  ('shadowing',                      23, 100, 1, 'seed', false),
  ('luyennoi',                       23, 100, 1, 'seed', false),
  ('luyennghe',                      23, 100, 1, 'seed', false),
  ('englishlistening',               23, 100, 1, 'seed', false),
  ('englishspeaking',                23, 100, 1, 'seed', false),
  ('hoctienghan_chonguoimoibatdau',  23, 100, 1, 'seed', false),
  ('tienghancoban',                  23, 100, 1, 'seed', false),
  ('hoctiengnhat_jlpt',              23, 100, 1, 'seed', false),
  ('tiengnhatcoban',                 23, 100, 1, 'seed', false),
  ('hoctiengtrung_chonguoimoibatdau',23, 100, 1, 'seed', false),
  ('tiengtrungcoban',                23, 100, 1, 'seed', false),
  ('hoctiengphap_coban',             23, 100, 1, 'seed', false),
  ('hoctiengduc',                    23, 100, 1, 'seed', false),
  ('hoctiengtaybanha',               23, 100, 1, 'seed', false),
  ('polyglot',                       23, 100, 1, 'seed', false),
  ('langtok',                        23, 100, 1, 'seed', false),
  ('languagetok',                    23, 100, 1, 'seed', false),
  ('englishteacher',                 23, 100, 1, 'seed', false),
  ('nativetutor',                    23, 100, 1, 'seed', false),
  ('langlearner',                    23, 100, 1, 'seed', false),
  ('duolingostreak',                 23, 100, 1, 'seed', false),
  ('tienganhgiaotiep',               23, 100, 1, 'seed', false),
  ('tienganhcongviec',               23, 100, 1, 'seed', false),
  ('englishforwork',                 23, 100, 1, 'seed', false),
  ('englishforbusiness',             23, 100, 1, 'seed', false),
  ('englishforchildren',             23, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
