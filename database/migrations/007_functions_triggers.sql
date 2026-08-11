-- 007_functions_triggers.sql
-- Server-side logic that the Mongo services did (unreliably) in application code:
--   * timestamps are written server-side only
--   * firm_url is generated atomically on insert
--   * email is immutable
--   * like/comment counters stay in sync with the engagement tables

-- ---------------------------------------------------------------------------
-- slugify(): lowercase, collapse non-alphanumerics to '-', trim leading/trailing '-'.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION slugify(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE AS $$
    SELECT trim(both '-' from regexp_replace(lower(coalesce(txt, '')), '[^a-z0-9]+', '-', 'g'));
$$;

-- ---------------------------------------------------------------------------
-- set_updated_at(): refresh updated_at on every UPDATE. The server is the sole writer of
-- timestamps (Mongo's strip_client_timestamps intent, enforced instead of hoped for).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at                BEFORE UPDATE ON users                FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER organizations_set_updated_at        BEFORE UPDATE ON organizations        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER user_connections_set_updated_at     BEFORE UPDATE ON user_connections     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER organization_follows_set_updated_at BEFORE UPDATE ON organization_follows FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER firm_member_requests_set_updated_at BEFORE UPDATE ON firm_member_requests FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER posts_set_updated_at                BEFORE UPDATE ON posts                FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER articles_set_updated_at             BEFORE UPDATE ON articles             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER comments_set_updated_at             BEFORE UPDATE ON comments             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER likes_set_updated_at                BEFORE UPDATE ON likes                FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- generate_firm_url(): build "{slug}-{id}" on insert. NEW.id is already populated by the
-- column default at BEFORE INSERT time, so this is atomic in one round trip (vs. Mongo's
-- insert-then-update, which could leave a firm with no public URL on a crash between).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generate_firm_url() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.firm_url IS NULL OR NEW.firm_url = '' THEN
        NEW.firm_url := slugify(NEW.name) || '-' || NEW.id::text;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER organizations_firm_url
    BEFORE INSERT ON organizations
    FOR EACH ROW EXECUTE FUNCTION generate_firm_url();

-- ---------------------------------------------------------------------------
-- enforce_email_immutable(): email is the natural key; reject any change to it.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION enforce_email_immutable() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.email IS DISTINCT FROM OLD.email THEN
        RAISE EXCEPTION 'users.email is immutable (attempted % -> %)', OLD.email, NEW.email
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_email_immutable
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION enforce_email_immutable();

-- ---------------------------------------------------------------------------
-- Denormalized counters. AFTER INSERT/DELETE on likes/comments keep the parent's counts
-- correct. Replaces the doc's unbounded distinct()+$in counting. During a cascade delete of a
-- parent (post/article/comment), the counter UPDATE simply matches zero rows -> harmless no-op.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION likes_maintain_counts() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.post_id    IS NOT NULL THEN UPDATE posts    SET like_count = like_count + 1 WHERE id = NEW.post_id;    END IF;
        IF NEW.article_id IS NOT NULL THEN UPDATE articles SET like_count = like_count + 1 WHERE id = NEW.article_id; END IF;
        IF NEW.comment_id IS NOT NULL THEN UPDATE comments SET like_count = like_count + 1 WHERE id = NEW.comment_id; END IF;
        RETURN NEW;
    ELSE  -- DELETE
        IF OLD.post_id    IS NOT NULL THEN UPDATE posts    SET like_count = like_count - 1 WHERE id = OLD.post_id;    END IF;
        IF OLD.article_id IS NOT NULL THEN UPDATE articles SET like_count = like_count - 1 WHERE id = OLD.article_id; END IF;
        IF OLD.comment_id IS NOT NULL THEN UPDATE comments SET like_count = like_count - 1 WHERE id = OLD.comment_id; END IF;
        RETURN OLD;
    END IF;
END;
$$;

CREATE TRIGGER likes_maintain_counts_aid
    AFTER INSERT OR DELETE ON likes
    FOR EACH ROW EXECUTE FUNCTION likes_maintain_counts();

CREATE OR REPLACE FUNCTION comments_maintain_counts() RETURNS trigger
    LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.post_id    IS NOT NULL THEN UPDATE posts    SET comment_count = comment_count + 1 WHERE id = NEW.post_id;    END IF;
        IF NEW.article_id IS NOT NULL THEN UPDATE articles SET comment_count = comment_count + 1 WHERE id = NEW.article_id; END IF;
        RETURN NEW;
    ELSE  -- DELETE
        IF OLD.post_id    IS NOT NULL THEN UPDATE posts    SET comment_count = comment_count - 1 WHERE id = OLD.post_id;    END IF;
        IF OLD.article_id IS NOT NULL THEN UPDATE articles SET comment_count = comment_count - 1 WHERE id = OLD.article_id; END IF;
        RETURN OLD;
    END IF;
END;
$$;

CREATE TRIGGER comments_maintain_counts_aid
    AFTER INSERT OR DELETE ON comments
    FOR EACH ROW EXECUTE FUNCTION comments_maintain_counts();
