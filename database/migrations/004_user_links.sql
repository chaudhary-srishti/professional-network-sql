-- 004_user_links.sql
-- Mongo modelled three different relationships in ONE collection (USER_LINKS), discriminated
-- by link_type, with a heterogeneous, order-significant participants[] array. That array is
-- exactly the quirk to eliminate relationally: it can't be FK-enforced, can't be deduped
-- (["A","B"] != ["B","A"]), and its positional semantics are load-bearing.
--
-- We split it into three purpose-built tables with typed FK columns and per-type status rules.

-- Shared status enum for the two request-style relationships.
CREATE TYPE link_status AS ENUM ('pending', 'accepted', 'rejected');

-- 1) user <-> user connection (Mongo link_type='user').
CREATE TABLE user_connections (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- participants[0]
    target_id          uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- participants[1]
    status             link_status NOT NULL DEFAULT 'pending',
    personal_note      text,                                    -- context.personal_note
    status_updated_at  timestamptz NOT NULL DEFAULT now(),      -- state.updated_at
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT user_connections_distinct_ck CHECK (requester_id <> target_id)
    -- Undirected uniqueness (no [A,B] + [B,A] dupes) via a LEAST/GREATEST unique index in 009.
);

COMMENT ON TABLE user_connections IS 'Mongo USER_LINKS link_type=user; requester_id=initiator, target_id=recipient.';

-- 2) user -> firm follow (Mongo link_type='organization', status always "following").
-- Modelled as a plain edge: the row existing IS the follow. No status column needed.
CREATE TABLE organization_follows (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,  -- follower
    organization_id  uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,  -- firm
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT organization_follows_uq UNIQUE (user_id, organization_id)  -- idempotent follow
);

COMMENT ON TABLE organization_follows IS 'Mongo USER_LINKS link_type=organization; unfollow = delete row.';

-- 3) user -> firm membership request (Mongo link_type='firm_member_request').
-- On acceptance the application inserts into organization_members (role='owner' on claim).
CREATE TABLE firm_member_requests (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,  -- applicant
    organization_id    uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,  -- firm
    status             link_status NOT NULL DEFAULT 'pending',
    personal_note      text,
    status_updated_at  timestamptz NOT NULL DEFAULT now(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT firm_member_requests_uq UNIQUE (user_id, organization_id)  -- one request per pair
);

COMMENT ON TABLE firm_member_requests IS 'Mongo USER_LINKS link_type=firm_member_request.';
