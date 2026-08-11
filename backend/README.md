# Professional Network — SQL Backend

FastAPI service over the professional-network relational schema. **Raw parameterized SQL** via `asyncpg` —
no ORM, so every query is visible in `app/repositories/`. The backend does **record CRUD +
domain actions only**; it contains no migration/DDL logic. The schema is owned by
`database/migrations/` (apply with `make migrate` from the repo root).

## Run

**Containerized (from repo root):**

```bash
make stack                     # db + migrate + seed + build/run this backend
make logs                      # follow API logs
```

**Local dev (from backend/), against the docker Postgres:**

```bash
# 1. schema (from repo root): make up && make migrate   (optionally: make seed)
# 2. backend (from backend/):
uv sync                        # creates .venv on Python 3.12
cp .env.example .env           # DATABASE_URL points at localhost:5433/professional_network
uv run uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the interactive API.

## Auth (dev stub)

Requests act as the user named in the **`X-User-Email`** header (mirrors the platform's "resolve the
Firebase user by email"). Mutations take the actor from this header, never the request body —
the fix for the original "engagement writes trust `user_id` from the body" bug. Swap
`app/security.py` for a real JWT verifier in production.

```bash
curl -s localhost:8000/users -X POST -H 'content-type: application/json' \
  -d '{"email":"alice@x.com","name":"Alice"}'
curl -s localhost:8000/posts -X POST -H 'X-User-Email: alice@x.com' \
  -H 'content-type: application/json' -d '{"hashtags":["finance"]}'
```

## Layout

```
app/
  main.py            FastAPI app + asyncpg pool lifespan
  config.py          settings (DATABASE_URL)
  db.py              pool + get_conn dependency
  security.py        X-User-Email -> current_user
  errors.py          asyncpg SQLSTATE -> HTTP status
  schemas.py         Pydantic request/response models
  repositories/      raw SQL, one module per aggregate
  routers/           thin HTTP layer -> repositories
tests/               pytest e2e against a professional_network_test DB
```

## Endpoints (summary)

- **users**: `POST /users` (get-or-create), `GET /users`, `GET /users/{id}`, `PATCH`, `DELETE`,
  `GET /users/{id}/stats`, `GET /users/{id}/posts`
- **organizations**: CRUD, `GET /organizations/{id}/stats|members|followers|posts`,
  `POST|DELETE /organizations/{id}/members`
- **links**: `POST /connections`, `POST /connections/{id}/accept|reject`, `DELETE`,
  `GET /connections`; `POST /follows`, `DELETE /follows/{org}`, `GET /follows`;
  `POST /member-requests`, `POST /member-requests/{id}/accept|reject`
- **posts**: `POST /posts`, `GET /posts?hashtag=`, `GET /posts/{id}`, `PATCH`, `DELETE`
- **articles**: `POST /articles`, `GET /articles`, `GET /articles/{id}`, `PATCH`, `DELETE`
- **engagement**: `POST|GET /posts/{id}/comments`, `POST|GET /articles/{id}/comments`,
  `DELETE /comments/{id}`; `POST|DELETE /{posts|articles|comments}/{id}/likes`

## Tests

```bash
uv sync --extra dev
uv run pytest            # builds/refreshes professional_network_test from migrations/, truncates per test
```

Covers: like idempotency, author-only post delete, connection accept-only-by-target,
duplicate-connection 409, email not client-updatable, and the firm member-request flow.
