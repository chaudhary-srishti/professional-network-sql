-- 010_postgis_optional.sql   (OPTIONAL — requires the PostGIS extension)
--
-- The Mongo Location.geo was a GeoJSON Point needing a 2dsphere index for $near/$geoWithin
-- (which the repo never created). This migration adds the relational equivalent: a
-- geography(Point,4326) column derived from the lon/lat numerics, plus a GiST index.
--
-- Skipped by `make migrate` because stock postgres:16 has no PostGIS. Apply on a PostGIS-
-- enabled server (image postgis/postgis) with `make postgis`.

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE users         ADD COLUMN IF NOT EXISTS location_geo geography(Point, 4326);
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS location_geo geography(Point, 4326);

-- Backfill from existing lon/lat.
UPDATE users
   SET location_geo = ST_SetSRID(ST_MakePoint(location_longitude, location_latitude), 4326)::geography
 WHERE location_longitude IS NOT NULL AND location_geo IS NULL;

UPDATE organizations
   SET location_geo = ST_SetSRID(ST_MakePoint(location_longitude, location_latitude), 4326)::geography
 WHERE location_longitude IS NOT NULL AND location_geo IS NULL;

CREATE INDEX IF NOT EXISTS users_geo_gist         ON users         USING gist (location_geo);
CREATE INDEX IF NOT EXISTS organizations_geo_gist ON organizations USING gist (location_geo);

-- Example proximity query (users within 50km of a point):
--   SELECT name FROM users
--    WHERE ST_DWithin(location_geo, ST_MakePoint(-73.9857, 40.7484)::geography, 50000);
