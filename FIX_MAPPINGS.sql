-- ============================================
-- FIX AI MAPPINGS - CRITICAL DATABASE REPAIR
-- ============================================

-- 1. Kiểm tra Foreign Key constraints
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'ai_mappings';

-- 2. Xóa các mapping bị lỗi (null foreign keys)
DELETE FROM public.ai_mappings
WHERE social_target_id IS NULL
   OR discord_channel_id IS NULL;

-- 3. Cập nhật tất cả mapping có status NULL thành 'approved'
UPDATE public.ai_mappings
SET status = 'approved'
WHERE status IS NULL OR status = '';

-- 4. Cập nhật tất cả mapping có confidence_score NULL thành 1.0
UPDATE public.ai_mappings
SET confidence_score = 1.0
WHERE confidence_score IS NULL;

-- 5. Đảm bảo reviewed_at được set cho các mapping approved
UPDATE public.ai_mappings
SET reviewed_at = COALESCE(reviewed_at, updated_at, created_at)
WHERE status = 'approved' AND reviewed_at IS NULL;

-- 6. Kiểm tra dữ liệu sau khi fix
SELECT
    am.id,
    am.status,
    am.confidence_score,
    st.display_name AS target_name,
    st.platform,
    dc.channel_name,
    dc.guild_name
FROM public.ai_mappings am
LEFT JOIN public.social_targets st ON am.social_target_id = st.id
LEFT JOIN public.discord_channels dc ON am.discord_channel_id = dc.id
ORDER BY am.created_at DESC;

-- 7. Đếm số lượng mapping theo status
SELECT
    status,
    COUNT(*) as count
FROM public.ai_mappings
GROUP BY status;

-- 8. Tìm các target chưa có mapping
SELECT
    st.id,
    st.platform,
    st.display_name,
    st.target_url,
    st.is_active
FROM public.social_targets st
LEFT JOIN public.ai_mappings am ON st.id = am.social_target_id
WHERE am.id IS NULL
    AND st.is_active = true;

-- 9. Tìm các mapping trỏ đến target hoặc channel không tồn tại
SELECT
    am.id,
    am.social_target_id,
    am.discord_channel_id,
    CASE
        WHEN st.id IS NULL THEN 'Target not found'
        WHEN dc.id IS NULL THEN 'Channel not found'
        ELSE 'OK'
    END as issue
FROM public.ai_mappings am
LEFT JOIN public.social_targets st ON am.social_target_id = st.id
LEFT JOIN public.discord_channels dc ON am.discord_channel_id = dc.id
WHERE st.id IS NULL OR dc.id IS NULL;

-- 10. Xóa các mapping orphan (trỏ đến target/channel không tồn tại)
DELETE FROM public.ai_mappings
WHERE social_target_id NOT IN (SELECT id FROM public.social_targets)
   OR discord_channel_id NOT IN (SELECT id FROM public.discord_channels);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Kiểm tra tổng quan
SELECT
    'Total Mappings' as metric,
    COUNT(*) as value
FROM public.ai_mappings
UNION ALL
SELECT
    'Approved Mappings',
    COUNT(*)
FROM public.ai_mappings
WHERE status = 'approved'
UNION ALL
SELECT
    'Pending Mappings',
    COUNT(*)
FROM public.ai_mappings
WHERE status = 'pending'
UNION ALL
SELECT
    'Active Targets',
    COUNT(*)
FROM public.social_targets
WHERE is_active = true
UNION ALL
SELECT
    'Active Channels',
    COUNT(*)
FROM public.discord_channels
WHERE is_active = true;
