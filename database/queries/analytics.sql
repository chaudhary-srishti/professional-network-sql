-- analytics.sql
-- Example read queries against the seeded database. Each block is independent — run them
-- individually. They demonstrate the relational tooling the Mongo version lacked:
-- window functions, CTEs, self-joins, array/GIN filtering, and trigram search.
-- (Free-text body search is TurboPuffer's job and is intentionally not modeled here.)

-- 1) Global feed, newest first, with a running row number.
SELECT ROW_NUMBER() OVER (ORDER BY updated_at DESC) AS rank,
       id, author_name, firm_name, like_count, comment_count, updated_at
FROM post_feed
ORDER BY updated_at DESC;

-- 2) Most-engaged post per author (window RANK partitioned by author).
SELECT author_name, id, like_count, comment_count
FROM (
    SELECT pf.*,
           RANK() OVER (PARTITION BY author_id ORDER BY like_count DESC, updated_at DESC) AS rnk
    FROM post_feed pf
) ranked
WHERE rnk = 1
ORDER BY like_count DESC;

-- 3) Hashtag filtering via GIN array containment (posts tagged BOTH finance and markets vs. either).
SELECT id, author_id, hashtags FROM posts WHERE hashtags @> ARRAY['finance','markets'];   -- all of
SELECT id, author_id, hashtags FROM posts WHERE hashtags && ARRAY['crypto','equities'];    -- any of

-- 4) Partial name search (the Mongo "$regex" on name) via trigram similarity + ILIKE.
SELECT id, name, current_title, similarity(name, 'nguyen') AS score
FROM users
WHERE name ILIKE '%nguy%'
ORDER BY score DESC;

-- 5) Mutual connections between two users (self-join over the undirected edge view).
WITH me  AS (SELECT other_user_id FROM user_connection_edges
             WHERE user_id = 'a0000000-0000-0000-0000-000000000001' AND status = 'accepted'),
     you AS (SELECT other_user_id FROM user_connection_edges
             WHERE user_id = 'a0000000-0000-0000-0000-000000000004' AND status = 'accepted')
SELECT u.name
FROM me JOIN you USING (other_user_id)
JOIN users u ON u.id = me.other_user_id;

-- 6) Hashtag popularity rollup (unnest the array, then aggregate).
SELECT tag, count(*) AS posts
FROM posts, unnest(hashtags) AS tag
GROUP BY tag
ORDER BY posts DESC, tag;

-- 7) Cumulative follower growth per firm over time (CTE + window running total).
WITH daily AS (
    SELECT organization_id, date_trunc('day', created_at) AS day, count(*) AS new_followers
    FROM organization_follows
    GROUP BY organization_id, date_trunc('day', created_at)
)
SELECT o.name, d.day, d.new_followers,
       SUM(d.new_followers) OVER (PARTITION BY d.organization_id ORDER BY d.day) AS cumulative_followers
FROM daily d JOIN organizations o ON o.id = d.organization_id
ORDER BY o.name, d.day;

-- 8) Pending connection requests received by each user (positional query, now a plain filter).
SELECT u.name AS recipient, requester.name AS from_user, e.created_at
FROM user_connection_edges e
JOIN users u         ON u.id = e.user_id
JOIN users requester ON requester.id = e.other_user_id
WHERE e.direction = 'incoming' AND e.status = 'pending'
ORDER BY u.name;

-- 9) Counter integrity check: denormalized like_count vs. a live count. Should return 0 rows.
SELECT p.id, p.like_count AS stored, count(l.id) AS actual
FROM posts p
LEFT JOIN likes l ON l.post_id = p.id
GROUP BY p.id, p.like_count
HAVING p.like_count <> count(l.id);

-- 10) Firm leaderboard by total engagement on firm-attributed posts.
SELECT o.name,
       count(DISTINCT p.id)                         AS firm_posts,
       COALESCE(SUM(p.like_count), 0)               AS total_likes,
       COALESCE(SUM(p.comment_count), 0)            AS total_comments
FROM organizations o
LEFT JOIN posts p ON p.firm_id = o.id
GROUP BY o.name
ORDER BY total_likes DESC, o.name;
