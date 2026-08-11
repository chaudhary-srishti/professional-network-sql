-- 008_views.sql
-- Read models. In Mongo these were hand-rolled aggregation pipelines ($lookup author + firm +
-- two correlated engagement sub-pipelines per item) and fan-out stat counters. Here they are
-- plain views over normalized tables with real join keys.

-- ---------------------------------------------------------------------------
-- Feeds: content + resolved author + optional firm + denormalized counts.
-- Mirrors the Mongo read-enrichment shape (author projected to name/title/picture,
-- firm to url/name/logo) but as a single declarative join.
-- ---------------------------------------------------------------------------
CREATE VIEW post_feed AS
SELECT p.id,
       p.author_id,
       u.name          AS author_name,
       u.current_title AS author_title,
       u.profile_picture AS author_picture,
       p.firm_id,
       o.name          AS firm_name,
       o.firm_url      AS firm_url,
       o.logo          AS firm_logo,
       p.hashtags,
       p.images,
       p.shared_post_id,
       p.shared_article_id,
       p.like_count,
       p.comment_count,
       p.created_at,
       p.updated_at
FROM posts p
JOIN users u          ON u.id = p.author_id
LEFT JOIN organizations o ON o.id = p.firm_id;

CREATE VIEW article_feed AS
SELECT a.id,
       a.author_id,
       u.name          AS author_name,
       u.current_title AS author_title,
       u.profile_picture AS author_picture,
       a.firm_id,
       o.name          AS firm_name,
       o.firm_url      AS firm_url,
       o.logo          AS firm_logo,
       a.cover_image,
       a.images,
       a.like_count,
       a.comment_count,
       a.created_at,
       a.updated_at
FROM articles a
JOIN users u          ON u.id = a.author_id
LEFT JOIN organizations o ON o.id = a.firm_id;

-- ---------------------------------------------------------------------------
-- user_connection_edges: one row per (user, other_user) with direction. Flattens the
-- undirected user_connections table so "my network" is a single-column filter, replacing the
-- Mongo positional {participants.0}/{participants.1} query gymnastics.
-- ---------------------------------------------------------------------------
CREATE VIEW user_connection_edges AS
SELECT c.id, c.requester_id AS user_id, c.target_id AS other_user_id,
       'outgoing'::text AS direction, c.status, c.created_at
FROM user_connections c
UNION ALL
SELECT c.id, c.target_id AS user_id, c.requester_id AS other_user_id,
       'incoming'::text AS direction, c.status, c.created_at
FROM user_connections c;

-- ---------------------------------------------------------------------------
-- Stats. Bounded aggregate queries in place of the doc's distinct()+$in fan-out (which pulled
-- every id a user/firm authored into memory).
-- ---------------------------------------------------------------------------
CREATE VIEW user_stats AS
SELECT u.id AS user_id,
       u.name,
       (SELECT count(*) FROM posts    p WHERE p.author_id = u.id) AS posts_count,
       (SELECT count(*) FROM articles a WHERE a.author_id = u.id) AS articles_count,
       (SELECT count(*) FROM comments c WHERE c.author_id = u.id) AS comments_count,
       (SELECT count(*) FROM user_connections uc
          WHERE uc.status = 'accepted'
            AND (uc.requester_id = u.id OR uc.target_id = u.id))  AS connections_count,
       (SELECT count(*) FROM user_connections uc
          WHERE uc.status = 'pending' AND uc.target_id = u.id)    AS pending_requests_count,
       (SELECT count(*) FROM organization_follows f
          WHERE f.user_id = u.id)                                 AS following_count,
       -- likes received across the user's own posts + articles
       (SELECT count(*)
          FROM likes l
          LEFT JOIN posts    p ON p.id = l.post_id
          LEFT JOIN articles a ON a.id = l.article_id
          WHERE p.author_id = u.id OR a.author_id = u.id)         AS likes_received_count
FROM users u;

CREATE VIEW firm_stats AS
SELECT o.id AS firm_id,
       o.name,
       (SELECT count(*) FROM organization_members m WHERE m.organization_id = o.id) AS members_count,
       (SELECT count(*) FROM organization_follows f WHERE f.organization_id = o.id) AS followers_count,
       (SELECT count(*) FROM firm_member_requests r
          WHERE r.organization_id = o.id AND r.status = 'pending')                  AS pending_member_requests_count,
       (SELECT count(*) FROM posts    p WHERE p.firm_id = o.id)                     AS posts_count,
       (SELECT count(*) FROM articles a WHERE a.firm_id = o.id)                     AS articles_count
FROM organizations o;
