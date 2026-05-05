-- Align niche_taxonomy id=2 VN label with creator_niches beauty bucket (PR1):
-- middle dot (·) instead of slash (/). FE also maps via resolveNicheNameVn.
UPDATE public.niche_taxonomy
SET name_vn = 'Làm đẹp · Skincare'
WHERE id = 2;
