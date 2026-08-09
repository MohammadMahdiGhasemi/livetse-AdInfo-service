-- Run this against an existing database BEFORE stamping the Alembic baseline.
-- Every count should be 0 before applying revision 20260809_0002.

SELECT 'banners_invalid_time_range' AS check_name, COUNT(*) AS invalid_rows
FROM banners WHERE expire_at <= start_at
UNION ALL
SELECT 'banners_negative_sort_order', COUNT(*)
FROM banners WHERE sort_order < 0
UNION ALL
SELECT 'announcements_invalid_time_range', COUNT(*)
FROM announcements WHERE display_expire_at <= display_start_at
UNION ALL
SELECT 'ad_campaigns_required_nulls', COUNT(*)
FROM ad_campaigns
WHERE client_name IS NULL OR start_at IS NULL OR expire_at IS NULL OR is_active IS NULL
UNION ALL
SELECT 'ad_campaigns_invalid_time_range', COUNT(*)
FROM ad_campaigns
WHERE start_at IS NOT NULL AND expire_at IS NOT NULL AND expire_at <= start_at
UNION ALL
SELECT 'ad_assets_required_nulls', COUNT(*)
FROM ad_assets
WHERE campaign_id IS NULL OR platform IS NULL OR image_url IS NULL OR link_url IS NULL
UNION ALL
SELECT 'ad_stats_required_nulls', COUNT(*)
FROM ad_stats
WHERE asset_id IS NULL OR views_count IS NULL OR clicks_count IS NULL OR date IS NULL
UNION ALL
SELECT 'ad_stats_negative_values', COUNT(*)
FROM ad_stats
WHERE views_count < 0 OR clicks_count < 0;
