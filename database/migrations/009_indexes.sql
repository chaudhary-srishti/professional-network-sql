-- 009_indexes.sql
-- The Mongo repo created NO indexes in code (all managed out-of-band in Atlas). These are the
-- indexes the query patterns actually require, made explicit and version-controlled.

-- ---- users --------------------------------------------------------------------------------
-- Partial-match ("$regex") name search -> trigram GIN.
CREATE INDEX users_name_trgm       ON users USING gin (name gin_trgm_ops);
-- Audience filters (current_role/current_company $in).
CREATE INDEX users_current_title   ON users (current_title);
CREATE INDEX users_current_company ON users (current_company);
-- Admin listing / signup-window queries.
CREATE INDEX users_created_at      ON users (created_at DESC);
-- (email uniqueness/lookup already covered by the UNIQUE constraint's index.)

-- ---- organizations ------------------------------------------------------------------------
CREATE INDEX organizations_name_trgm      ON organizations USING gin (name gin_trgm_ops);
CREATE INDEX organizations_categories_gin ON organizations USING gin (categories);
CREATE INDEX organization_members_user    ON organization_members (user_id);  -- get_firms_by_member

-- ---- user_links (three tables) ------------------------------------------------------------
-- Undirected uniqueness: [A,B] and [B,A] collapse to one canonical key. This is the relational
-- fix for the Mongo "duplicate links possible under concurrency" problem.
CREATE UNIQUE INDEX user_connections_pair_uq
    ON user_connections (LEAST(requester_id, target_id), GREATEST(requester_id, target_id));
CREATE INDEX user_connections_requester ON user_connections (requester_id, status);
CREATE INDEX user_connections_target    ON user_connections (target_id, status);   -- requests received
CREATE INDEX organization_follows_org   ON organization_follows (organization_id); -- followers of firm
CREATE INDEX firm_member_requests_org   ON firm_member_requests (organization_id, status);

-- ---- posts / articles ---------------------------------------------------------------------
-- Feeds sort on updated_at DESC (per the Mongo spec's feed ordering).
CREATE INDEX posts_author_recent    ON posts (author_id, updated_at DESC);
CREATE INDEX posts_firm_recent      ON posts (firm_id, updated_at DESC);
CREATE INDEX posts_recent           ON posts (updated_at DESC);
CREATE INDEX posts_hashtags_gin     ON posts USING gin (hashtags);      -- hashtag containment
CREATE INDEX articles_author_recent ON articles (author_id, updated_at DESC);
CREATE INDEX articles_firm_recent   ON articles (firm_id, updated_at DESC);
CREATE INDEX articles_recent        ON articles (updated_at DESC);

-- ---- engagement ---------------------------------------------------------------------------
-- One like per (user, target): partial unique indexes enforce the Mongo logical key
-- (entity_id, user_id, type) and make a double-tap idempotent instead of count-inflating.
CREATE UNIQUE INDEX likes_user_post_uq    ON likes (user_id, post_id)    WHERE post_id    IS NOT NULL;
CREATE UNIQUE INDEX likes_user_article_uq ON likes (user_id, article_id) WHERE article_id IS NOT NULL;
CREATE UNIQUE INDEX likes_user_comment_uq ON likes (user_id, comment_id) WHERE comment_id IS NOT NULL;
-- Reverse lookups (who liked X) / comment listing sorted by recency.
CREATE INDEX likes_post_id       ON likes (post_id)    WHERE post_id    IS NOT NULL;
CREATE INDEX likes_article_id    ON likes (article_id) WHERE article_id IS NOT NULL;
CREATE INDEX likes_comment_id    ON likes (comment_id) WHERE comment_id IS NOT NULL;
CREATE INDEX comments_post_recent    ON comments (post_id, created_at)    WHERE post_id    IS NOT NULL;
CREATE INDEX comments_article_recent ON comments (article_id, created_at) WHERE article_id IS NOT NULL;
