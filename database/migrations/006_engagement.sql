-- 006_engagement.sql
-- Mongo used ONE polymorphic USERS_ENGAGEMENT collection for every interaction on every
-- content type (likes, replies, reply-likes, RSVPs, poll votes, reviews), with no
-- entity_collection discriminator and no unique index behind its logical (entity, user, type)
-- key. We split by interaction kind and, per the agreed scope, model only the post/article
-- surface: comments (replies) and likes (incl. likes on a reply).
--
-- Out of scope here (out-of-scope target entities): reviews, event_rsvp, poll_input,
-- and the *_like/*_reply variants for polls/events. They extend by the same pattern:
-- a typed table with FK'd target column(s) + a per-user unique constraint.

-- Replies. Flat threads only (Mongo has no parent_reply_id; nesting is exactly two levels).
CREATE TABLE comments (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id   uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,   -- actor
    firm_id     uuid          REFERENCES organizations(id) ON DELETE SET NULL,  -- acting as firm
    -- Exactly one target: a post OR an article.
    post_id     uuid REFERENCES posts(id)    ON DELETE CASCADE,
    article_id  uuid REFERENCES articles(id) ON DELETE CASCADE,
    body        text NOT NULL DEFAULT '',     -- Mongo `reply`, defaults ""
    like_count  integer NOT NULL DEFAULT 0,   -- reply_like count, maintained by trigger (007)
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT comments_target_one_ck CHECK (
        (post_id IS NOT NULL)::int + (article_id IS NOT NULL)::int = 1
    )
);

COMMENT ON TABLE comments IS 'Replies on posts/articles (Mongo *_reply). Flat; a reply-like targets this row.';

-- Likes. A like on a post, an article, or a comment (Mongo reply_like -> comment_id set).
-- The row existing IS the like; "unlike" deletes it (Mongo's delete-as-toggle). The per-target
-- partial unique indexes in 009 make a double-tap idempotent instead of a count-inflating dupe.
CREATE TABLE likes (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,   -- actor
    firm_id     uuid          REFERENCES organizations(id) ON DELETE SET NULL,  -- acting as firm
    -- Exactly one target: post OR article OR comment.
    post_id     uuid REFERENCES posts(id)    ON DELETE CASCADE,
    article_id  uuid REFERENCES articles(id) ON DELETE CASCADE,
    comment_id  uuid REFERENCES comments(id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT likes_target_one_ck CHECK (
        (post_id IS NOT NULL)::int + (article_id IS NOT NULL)::int + (comment_id IS NOT NULL)::int = 1
    )
);

COMMENT ON TABLE likes IS 'Likes on post/article/comment (Mongo *_like incl. reply_like). Unlike = delete.';
