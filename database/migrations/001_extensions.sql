-- 001_extensions.sql
-- Extensions used by the schema. All are IF NOT EXISTS so migrations are re-runnable.

-- gen_random_uuid(): opaque, client-generatable primary keys that mirror Mongo's ObjectId.
-- (gen_random_uuid() is in core since PG13; pgcrypto is kept for portability with PG12.)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- citext: case-insensitive text. Used for USERS.email so "A@x.com" == "a@x.com" and the
-- unique constraint that guards the get_or_create_user upsert can't be bypassed by case.
CREATE EXTENSION IF NOT EXISTS citext;

-- pg_trgm: trigram indexing. Backs partial ("$regex") name search on USERS/ORGANIZATIONS,
-- which the Mongo spec does with an unindexed $regex scan.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
