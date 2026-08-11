-- 005_posts_articles.sql
-- Content entities. Per the Mongo "two-store content model", the *searchable body text*
-- (post content, article title/content/tags, etc.) is owned by TurboPuffer and is NOT stored
-- here. Postgres holds structural metadata only, plus hashtags (used for structured filtering).
--
-- Relational changes vs. the Mongo doc:
--   * shared_entity (free-string entity_type + loose id) -> two nullable, FK-enforced columns
--     shared_post_id / shared_article_id with a CHECK that at most one is set.
--   * like_count / comment_count -> denormalized counters maintained by triggers (007),
--     replacing the unbounded distinct()+$in count pattern the doc calls out.
--
-- articles is created before posts because posts.shared_article_id references it.

CREATE TABLE articles (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id     uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,  -- required, immutable
    firm_id       uuid          REFERENCES organizations(id) ON DELETE SET NULL, -- posted as firm
    -- title / content / tags: TurboPuffer only (not stored here)
    cover_image   text,
    images        text[] NOT NULL DEFAULT '{}',
    like_count    integer NOT NULL DEFAULT 0,   -- maintained by trigger (007)
    comment_count integer NOT NULL DEFAULT 0,   -- maintained by trigger (007)
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE articles IS 'Long-form content metadata; title/content/tags live in TurboPuffer.';

CREATE TABLE posts (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id          uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,  -- required, immutable
    firm_id            uuid          REFERENCES organizations(id) ON DELETE SET NULL, -- posted as firm
    hashtags           text[] NOT NULL DEFAULT '{}',  -- duplicated to TurboPuffer for full-text
    images             text[] NOT NULL DEFAULT '{}',

    -- Repost / quote pointer. Mongo stored a free-string entity_type; here it is a typed,
    -- FK-enforced reference to exactly one of post/article (or none).
    shared_post_id     uuid REFERENCES posts(id)    ON DELETE SET NULL,
    shared_article_id  uuid REFERENCES articles(id) ON DELETE SET NULL,

    like_count         integer NOT NULL DEFAULT 0,   -- maintained by trigger (007)
    comment_count      integer NOT NULL DEFAULT 0,   -- maintained by trigger (007)
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT posts_shared_one_ck CHECK (
        (shared_post_id IS NOT NULL)::int + (shared_article_id IS NOT NULL)::int <= 1
    ),
    CONSTRAINT posts_no_self_share_ck CHECK (shared_post_id IS NULL OR shared_post_id <> id)
);

COMMENT ON TABLE posts IS 'Short-form content metadata; body text lives in TurboPuffer.';
