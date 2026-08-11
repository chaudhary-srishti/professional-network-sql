# Professional Network — Relational Schema Design

This is a PostgreSQL re-modeling of the platform's six core MongoDB collections. The source
`data-models.md` describes the Mongo design honestly — as a catalog of intentional
anti-patterns and known bugs. The goal here is a **clean, idiomatic relational schema** that
keeps the domain semantics and resolves those issues with real database tooling.

## Scope

Modeled: **users, organizations (+ members), user links, posts, articles, engagement
(comments + likes)**.

Out of scope (documented as extension points, same patterns apply): polls, events, products,
services, jobs, listings, and their review / RSVP / poll-vote interactions. Engagement is
therefore modeled only for the post/article surface (the spec's "post/article scope").

## Collection → table map

| Mongo collection | Postgres table(s) |
|---|---|
| `USERS` | `users` |
| `ORGANIZATIONS` | `organizations`, `organization_members` (embedded `members[]` promoted) |
| `USER_LINKS` (3 `link_type`s in one collection) | `user_connections`, `organization_follows`, `firm_member_requests` |
| `POSTS` | `posts` |
| `ARTICLES` | `articles` |
| `USERS_ENGAGEMENT` (polymorphic) | `comments`, `likes` |

## Key design decisions

- **UUID primary keys** (`gen_random_uuid()`) mirror Mongo `ObjectId`: opaque and
  client-generatable, which keeps the migration story simple. (bigint identity is a reasonable
  alternative if you prefer smaller, monotonic keys and don't need client-side generation.)
- **Two-store content model preserved.** Searchable free text (post content, article
  title/content/tags, user bio, firm description/overview) stays owned by TurboPuffer and is
  **not** stored here. Postgres holds structural metadata plus the two fields used for
  *structured* filtering: `posts.hashtags` (array containment) and `name` (trigram partial
  match). That's why there's no `tsvector`.
- **Location flattened.** Mongo's three legacy `location` shapes collapse into typed columns +
  `location_longitude/latitude`. The optional `010_postgis_optional.sql` derives a
  `geography(Point,4326)` column and a GiST index for `$near`/`$geoWithin`-style queries.
- **Engagement split by kind.** One polymorphic collection with a `type` enum and a
  `_TYPE_COLLECTION` lookup becomes typed tables with FK-enforced target columns. A "like" is
  a row; an "unlike" is a row delete (Mongo's delete-as-toggle), now made idempotent by
  per-target partial unique indexes.
- **Links split by relationship.** The heterogeneous, order-significant `participants[]` array
  becomes three tables with explicit `requester_id`/`target_id` or `user_id`/`organization_id`
  columns — no positional semantics to preserve.
- **Denormalized counters** (`like_count`, `comment_count`) maintained by triggers, replacing
  the unbounded `distinct()` + `$in` counting. Live-aggregate views are also provided.

## How each documented Mongo issue is resolved

| # (spec §9) | Mongo issue | Relational resolution |
|---|---|---|
| 1 | Engagement trusts `user_id` from request body | Out of DB scope (auth/API concern); FKs guarantee `user_id` at least references a real user |
| 2 | Post delete has no ownership check | API concern; `ON DELETE CASCADE` at least makes deletes clean |
| 3 | No indexes defined in code | `009_indexes.sql` — all required indexes version-controlled |
| — | `email` uniqueness unenforced (dup users) | `users_email_key UNIQUE` on `citext` |
| — | `firm_url` uniqueness is a check-then-act race | `organizations_firm_url_key UNIQUE` + atomic trigger generation |
| — | `firm_url` create is two non-atomic round trips | `generate_firm_url()` BEFORE INSERT (single statement) |
| 6 | User/firm delete doesn't cascade | FK `ON DELETE CASCADE` / `SET NULL` throughout |
| 8 | `distinct` + `$in` unbounded stat counting | trigger counters + bounded aggregate views (`user_stats`, `firm_stats`) |
| 10 | `category` vs `categories` field drift | single `categories text[]` |
| 13 | `poll_input` stored as string, documented int | out of scope (poll target); pattern noted |
| 14 | Link status can be accepted by the requester | modelable as a partial constraint / API check; status is a typed enum + `status_updated_at` |
| 16 | Plain-text password field | `password` column dropped entirely (auth in Firebase) |
| — | Members array drops members under concurrency | `organization_members` join table (no wholesale array `$set`) |
| — | `[A,B]` vs `[B,A]` duplicate links | `LEAST/GREATEST` canonical unique index on `user_connections` |
| — | Double-tap like inflates counts | per-target partial unique indexes on `likes` |

Issues that are inherently application/API-layer (1, 2, 9, 11, 12, and the notification
behavior) are noted but not "fixable" purely in schema — the schema removes the data-integrity
class of bugs.

## Triggers (see `007_functions_triggers.sql`)

- `set_updated_at()` — server is the sole writer of `updated_at`.
- `generate_firm_url()` — atomic slug generation on insert.
- `enforce_email_immutable()` — rejects any change to `users.email`.
- `likes_maintain_counts()` / `comments_maintain_counts()` — keep denormalized counters in sync.

## Extending to the out-of-scope entities

Add the target table (e.g. `polls`), then follow the established pattern: a typed interaction
table (`poll_votes`, `event_rsvps`, `reviews`) with an FK to its target and a per-user unique
constraint. Likes/comments already generalize — add a nullable FK column + a branch in the
`CHECK` and the counter trigger, plus a partial unique index.
