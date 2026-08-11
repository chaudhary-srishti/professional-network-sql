DB_USER  ?= professional_network
DB_NAME  ?= professional_network
COMPOSE  ?= docker compose
PSQL      = $(COMPOSE) exec -T db psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME)

.PHONY: up wait down migrate seed reset psql postgis api stack logs help

help:
	@echo "make up       - start Postgres 16 (docker) and wait until ready"
	@echo "make migrate  - apply database/migrations/001..009 (skips the optional PostGIS one)"
	@echo "make seed     - load sample data"
	@echo "make reset    - drop everything, recreate, migrate, seed"
	@echo "make postgis  - apply the optional PostGIS migration (needs PostGIS)"
	@echo "make api      - build & start the backend container (depends on db)"
	@echo "make stack    - up + migrate + seed + api (full one-command bring-up)"
	@echo "make logs     - follow the backend container logs"
	@echo "make psql     - open an interactive psql shell"
	@echo "make down     - stop the containers"

up:
	$(COMPOSE) up -d db
	$(MAKE) wait

wait:
	@echo "waiting for postgres..."
	@until $(COMPOSE) exec -T db pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1; do sleep 1; done
	@echo "postgres is ready"

migrate:
	@for f in database/migrations/*.sql; do \
		case "$$f" in *optional*) echo "skipping $$f (optional)"; continue;; esac; \
		echo "applying $$f"; \
		$(PSQL) -f - < "$$f" || exit 1; \
	done

seed:
	$(PSQL) -f - < database/seed/seed.sql

postgis:
	$(PSQL) -f - < database/migrations/010_postgis_optional.sql

reset:
	$(COMPOSE) down -v
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed

api:
	$(COMPOSE) up -d --build backend

stack:
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed
	$(MAKE) api

logs:
	$(COMPOSE) logs -f backend

psql:
	$(COMPOSE) exec db psql -U $(DB_USER) -d $(DB_NAME)

down:
	$(COMPOSE) down
