# Professional Network (SQL)

*Clean PostgreSQL data models + a raw-SQL FastAPI backend for a LinkedIn-style professional network — no ORM.*

A reference implementation that re-models a **document-database social-platform schema** as a
clean **PostgreSQL relational design**, with a thin **FastAPI backend** (raw SQL, no ORM) on top.

> The product is a LinkedIn-style professional networking platform — users, firms, a social
> graph, posts/articles, and engagement. These docs refer to it generically as **the Platform**.

---

## TL;DR

- **`database/`** — the relational schema as numbered SQL migrations, plus seed data, example
  analytical queries, and design docs. This is the system of record.
- **`backend/`** — a FastAPI service exposing CRUD + domain actions over the schema, written in
  **raw parameterized SQL** via `asyncpg`. Contains no migration/DDL logic.
- **Two-store content model** — structured data lives in PostgreSQL; **searchable free text
  lives in a dedicated search engine (TurboPuffer)**. See [Why TurboPuffer](#why-turbopuffer).
- **One command:** `make stack` brings up Postgres + the API in containers.

---

## Background & goals

The schema was reverse-engineered from an existing **MongoDB** design whose specification read
as a candid catalog of document-database anti-patterns and bugs: polymorphic references with no
foreign-key enforcement, no unique constraints or indexes, embedded arrays that drop data under
concurrency, field-name drift, plain-text passwords, unbounded stat counting, and missing delete
cascades.

The goal here is a design that **keeps the domain semantics but eliminates the data-integrity
class of problems** using real relational tooling — and reads as production-quality, idiomatic
PostgreSQL rather than a mechanical document-to-table dump.

---

## Architecture

```
                 ┌─────────────────────────────────────────┐
   HTTP clients  │            FastAPI backend               │
  ───────────────▶  routers → repositories (raw SQL)        │
                 │  actor resolved server-side (auth stub)  │
                 └───────────┬─────────────────────┬────────┘
                             │ transactional        │ free-text / semantic
                             │ (integrity, joins)   │ search
                             ▼                       ▼
                   ┌───────────────────┐   ┌───────────────────────┐
                   │    PostgreSQL     │   │   TurboPuffer          │
                   │  system of record │   │  search index         │
                   │  metadata + graph │   │  post/article/bio text │
                   └───────────────────┘   └───────────────────────┘
```

- **PostgreSQL** owns everything that needs integrity, relationships, and exact queries:
  identities, the social graph, content metadata, and engagement.
- **TurboPuffer** owns everything that needs ranked full-text and semantic search: post bodies,
  article title/content/tags, user bios, firm descriptions. Read paths fetch ids from search and
  hydrate them from Postgres.
- The **backend** is deliberately thin: HTTP → a repository function → one or two SQL statements.

---

## Why it's designed this way

### A relational core with enforced integrity
Every cross-entity reference is a real **foreign key**; every uniqueness rule (`email`, firm
slug, one-like-per-target, undirected connection pairs) is a **constraint or unique index**, not
an application-level "check then write" that races under concurrency. Deletes **cascade** through
FKs instead of orphaning content. The database refuses to hold invalid state — the application
cannot corrupt it by forgetting a check.

### Raw SQL, no ORM
Repositories contain hand-written, parameterized SQL. This makes every query, index usage, and
constraint visible and reviewable; there are no hidden N+1s or ORM-generated surprises. The
trade is more boilerplate and manual row-to-model mapping — accepted deliberately, since the SQL
*is* the point of this project.

### Push invariants into the database
Rules that must always hold live server-side in the schema, not in hopeful application code:
- **Triggers** keep `updated_at` authoritative, generate the firm slug atomically on insert, and
  enforce email immutability.
- **Denormalized counters** (`like_count`, `comment_count`) are maintained by triggers, so a
  feed read is O(1) instead of the original unbounded `distinct()` + `$in` fan-out.
- **Views** (`post_feed`, `article_feed`, `user_stats`, `firm_stats`) replace hand-rolled
  aggregation pipelines with declarative, reusable read models.

### Splitting polymorphic document shapes
The document design overloaded single collections: one "links" collection modeled three
different relationships via a positional array, and one "engagement" collection modeled every
interaction type. Relationally these become **purpose-built tables** (`user_connections`,
`organization_follows`, `firm_member_requests`; `comments`, `likes`) with typed FK columns and
per-relationship constraints. Polymorphic targets (a like on a post *or* article *or* comment)
use nullable FK columns + a `CHECK` that exactly one is set, plus partial unique indexes.

### Two-store content model
Structured data and searchable text are **different workloads**, so they live in different
stores. Postgres keeps only what it's good at (metadata, relationships, exact/structured
filters). Free text goes to a search engine. Postgres still keeps `hashtags` (array containment)
and `name` (trigram) because those are *structured filters*, not free-text ranking.

---

## Why TurboPuffer

**TurboPuffer** is a search-and-retrieval database built directly on **object storage**, offering
both **vector (semantic) search** and **full-text (BM25 keyword) search** with serverless,
usage-based economics. It owns the Platform's searchable text.

**Why a dedicated search store at all:**

1. **Search is not an OLTP workload.** Free-text and semantic search over posts, articles, and
   bios is fuzzy, ranking-oriented, and read-heavy — the opposite of the exact, integrity-first
   queries the relational core is tuned for. Mixing them degrades both.
2. **It keeps the relational database lean.** Large bodies of text plus the heavy inverted /
   `tsvector` / vector indexes they require would bloat tables, slow every write, and enlarge
   backups. Holding only metadata in Postgres keeps the OLTP store small and fast.
3. **Hybrid & semantic retrieval.** Social content benefits from embedding-based "find related"
   search *and* keyword search. TurboPuffer does both natively; plain relational full-text does
   not without bolting on a vector extension and custom ranking.

**Why TurboPuffer specifically:**

| Property | Payoff for the Platform |
|---|---|
| Built on object storage | Cheap to store a large, growing content corpus; storage decoupled from compute |
| Serverless, usage-based | No search cluster to size, patch, or keep warm; cost tracks usage |
| Native vector + BM25 (hybrid) | Semantic + keyword search from one system, no second index to reconcile |
| Independent scaling | Search-traffic spikes don't contend with transactional writes; failures are isolated |

**Alternatives considered:**

| Option | Why not the default here |
|---|---|
| **Postgres FTS (`tsvector`) + `pgvector`** | Simplest (one store) and a great fit at small scale — but couples heavy text/vector indexes to the OLTP database, adds write-time index maintenance, and makes vector search at scale contend with transactional load. Chosen against to keep the relational core lean. |
| **Elasticsearch / OpenSearch** | Very capable, but heavyweight to operate (cluster sizing, JVM tuning, shard management) and carries fixed cost even when idle. |
| **Algolia / hosted keyword search** | Excellent keyword DX, but weaker/opaque for vector + hybrid search and costly as volume grows. |

**The tradeoff we accept:** a two-store model means content is **dual-written**, so search is
**eventually consistent** with the source of truth, and a partial write can leave a document
indexed-but-missing or stored-but-unindexed. (The original code did this with fire-and-forget
writes — exactly the failure mode to avoid.) The correct mitigation is a **transactional outbox
+ retry** (write to Postgres, enqueue the index update, apply asynchronously with retries), not
best-effort background tasks. This adds operational surface and a second system to run — the
price of using the right tool for each workload.

---

## Design decisions & tradeoffs (summary)

| Decision | Why | Tradeoff |
|---|---|---|
| UUID primary keys | Mirror document ids; client-generatable; no sequence coordination | Larger than bigint; random UUIDs hurt index locality (use UUIDv7 if it matters) |
| Raw SQL, no ORM | Transparency, control, no hidden queries | More boilerplate; manual mapping |
| Typed tables for polymorphic shapes | FK integrity + per-relationship constraints | More tables; nullable-FK + CHECK pattern for shared shapes |
| Trigger-maintained counters | O(1) count reads; bounded work | Write amplification; logic lives in triggers |
| Two-store content (PG + TurboPuffer) | Right store per workload; lean OLTP; hybrid search | Dual-write / eventual consistency; two systems to operate |
| Views for feeds & stats | Declarative, reusable reads | View cost can be non-obvious; not materialized by default |
| Header-based dev auth (`X-User-Email`) | Actor derived server-side (fixes actor-spoofing); pluggable | Not production auth — swap for JWT/OIDC |
| Numbered SQL migrations; backend has no DDL | Schema is a single, reviewable source of truth owned by the DB | Manual ordering; no auto-diff from models |

---

## Data model

`users` · `organizations` (+ `organization_members`) · `user_connections` ·
`organization_follows` · `firm_member_requests` · `posts` · `articles` · `comments` · `likes`

Full field-by-field mapping, the resolution of every documented source-schema bug, and the ERD:

- **[database/docs/schema-design.md](database/docs/schema-design.md)**
- **[database/docs/erd.md](database/docs/erd.md)**

---

## Getting started

Requires Docker. `make` targets wrap `docker compose` + `psql` inside the container, so a local
`psql` is not needed.

**Database only:**

```bash
make up        # start Postgres 16
make migrate   # apply database/migrations/001..009
make seed      # load sample data
make psql      # then try queries from database/queries/analytics.sql
```

**Full stack (database + API, both containerized):**

```bash
make stack     # up + migrate + seed + build/run the backend
make logs      # follow API logs
```

API docs: **http://localhost:8000/docs**. Ports: Postgres **5433**, API **8000**.
`make reset` rebuilds the DB from scratch; `make postgis` applies the optional geospatial
migration (needs a PostGIS-enabled server); `make down` stops everything.

---

## Project layout

```
database/                     # everything schema-related (system of record)
  migrations/                 # 001..009 core, 010 optional PostGIS
  seed/seed.sql               # deterministic sample data
  queries/analytics.sql       # window functions, CTEs, self-joins, array/trigram search
  docs/                       # schema-design.md, erd.md
backend/                      # FastAPI + raw asyncpg service (see backend/README.md)
docker-compose.yml            # db (Postgres 16) + backend services
Makefile                      # up / migrate / seed / api / stack / reset / psql
```

---

## Testing

```bash
cd backend && uv sync --extra dev && uv run pytest
```

The suite builds a throwaway `*_test` database from the same migrations and runs end-to-end API
tests covering the integrity guarantees: like idempotency, author-only deletes, connection
accept-only-by-target, duplicate-connection conflict, email immutability, and the firm
member-request flow.
