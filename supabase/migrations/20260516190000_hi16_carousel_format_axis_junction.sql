-- HI-16 — Carousel-only format_axis values + full creator_niche coverage on junction.
--
-- Video ``format_axis`` slugs (talking_head_advice, vlog_daily, …) do not apply to
-- photo carousels. Five carousel axes mirror ``content_arc`` patterns; each of the
-- 16 UX creator_niches links to all five via ``creator_niche_content_classes``.

INSERT INTO content_classifications (id, slug, name_vn, name_en, format_axis, topic_axis, description_vn) VALUES
  (75, 'carousel_format_tutorial', 'Carousel hướng dẫn', 'Carousel tutorial', 'tutorial_carousel', 'carousel', 'Vuốt dạy từng bước, checklist, công thức slide-by-slide.'),
  (76, 'carousel_format_listicle', 'Carousel list / tips', 'Carousel listicle', 'listicle_carousel', 'carousel', 'Danh sách số, nhiều ý ngắn, tips xếp theo slide.'),
  (77, 'carousel_format_story', 'Carousel kể chuyện', 'Carousel story', 'story_carousel', 'carousel', 'Narrative vuốt, twist, tiến triển cảm xúc qua slide.'),
  (78, 'carousel_format_comparison', 'Carousel so sánh', 'Carousel comparison', 'comparison_carousel', 'carousel', 'Before/after, A vs B, đối chiếu hai phía.'),
  (79, 'carousel_format_gallery', 'Carousel gallery', 'Carousel gallery', 'gallery_carousel', 'carousel', 'Ảnh aesthetic, moodboard, lookbook — ít chữ, nhấn hình.')
ON CONFLICT (id) DO NOTHING;

SELECT setval(
  'content_classifications_id_seq',
  GREATEST(79, (SELECT COALESCE(MAX(id), 1) FROM content_classifications))
);

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
SELECT cn.id, c.id, TRUE
FROM creator_niches cn
CROSS JOIN content_classifications c
WHERE c.id BETWEEN 75 AND 79
ON CONFLICT (creator_niche_id, content_class_id) DO NOTHING;
