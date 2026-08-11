-- 003_organizations.sql
-- Firm / company page (Mongo ORGANIZATIONS), referenced everywhere as firm_id.
--
-- Relational changes vs. the Mongo doc:
--   * firm_url          -> UNIQUE + generated atomically in a BEFORE INSERT trigger (007),
--                          closing the check-then-act race and the two-round-trip create.
--   * category/categories -> unified to a single `categories text[]` (the doc's field-drift bug).
--   * members[]         -> promoted to a first-class join table organization_members, so a
--                          concurrent firm update can no longer silently drop a member.

CREATE TABLE organizations (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Public slug "{slugified-name}-{id}". Populated by trigger generate_firm_url (007);
    -- never supplied by clients. NOT NULL is satisfied by the trigger before the constraint check.
    firm_url              text NOT NULL,

    name                  text NOT NULL,       -- partial-match search -> pg_trgm index (009)
    description           text,                -- full-text search lives in TurboPuffer
    overview              text,                -- full-text search lives in TurboPuffer
    logo                  text,
    cover_photo           text,
    size                  text,                -- headcount band, e.g. "5-10"

    location_street       text,
    location_city         text,
    location_state        text,
    location_country      text,
    location_postal_code  text,
    location_longitude    numeric(9,6),
    location_latitude     numeric(9,6),

    categories            text[] NOT NULL DEFAULT '{}',  -- was category vs categories drift

    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT organizations_firm_url_key UNIQUE (firm_url),
    CONSTRAINT organizations_geo_pair_ck
        CHECK ((location_longitude IS NULL) = (location_latitude IS NULL))
);

COMMENT ON COLUMN organizations.firm_url   IS 'Auto-generated unique slug (trigger generate_firm_url, 007).';
COMMENT ON COLUMN organizations.categories IS 'Unifies the Mongo category/categories field drift.';

-- Firm membership. Was an embedded members[] array in Mongo; now a proper M:N join table.
CREATE TABLE organization_members (
    organization_id  uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          uuid NOT NULL REFERENCES users(id)         ON DELETE CASCADE,
    role             text NOT NULL DEFAULT 'member',            -- e.g. 'owner' on the claim path
    added_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

COMMENT ON TABLE organization_members IS 'Replaces Mongo embedded members[]; one row per membership.';
