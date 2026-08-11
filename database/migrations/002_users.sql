-- 002_users.sql
-- Canonical person record. In Mongo this is the schemaless USERS collection created lazily
-- on first Firebase login, with `email` as the natural join key.
--
-- Relational changes vs. the Mongo doc:
--   * email             -> citext + UNIQUE (was unenforced; the doc flags duplicate-user races)
--   * password          -> dropped entirely (plain-text field was dead code / a liability;
--                          authentication stays in Firebase, outside this database)
--   * super_admin       -> NOT NULL DEFAULT false, never silently absent
--   * current_role      -> renamed current_title (current_role is a reserved word in SQL)
--   * location.{...}    -> flattened, typed columns (the three legacy Mongo shapes collapse
--                          into one); optional PostGIS geo column added in 010_*.

CREATE TABLE users (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Natural key. Immutable after creation (enforced by a trigger in 007_*).
    email                 citext NOT NULL,

    name                  text,          -- partial-match ($regex) search -> pg_trgm index (009)
    current_title         text,          -- Mongo `current_role`; job title, audience $in filter
    current_company       text,          -- free text per spec, NOT a ref to organizations
    bio                   text,          -- full-text search lives in TurboPuffer, not here
    profile_picture       text,
    cover_photo           text,

    -- Flattened Location (shared shape with organizations). GeoJSON Point -> lon/lat numerics;
    -- the optional 010_postgis migration derives a geography(Point,4326) column from these.
    location_street       text,
    location_city         text,
    location_state        text,
    location_country      text,
    location_postal_code  text,
    location_longitude    numeric(9,6),
    location_latitude     numeric(9,6),

    super_admin           boolean NOT NULL DEFAULT false,

    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    last_login            timestamptz,

    CONSTRAINT users_email_key UNIQUE (email),
    -- lon and lat must be supplied together or not at all
    CONSTRAINT users_geo_pair_ck
        CHECK ((location_longitude IS NULL) = (location_latitude IS NULL))
);

COMMENT ON TABLE  users               IS 'Canonical person record; email is the natural key into Firebase auth.';
COMMENT ON COLUMN users.current_title IS 'Mongo field name was current_role (a reserved SQL word).';
COMMENT ON COLUMN users.email         IS 'Immutable after insert (trigger users_email_immutable in 007).';
