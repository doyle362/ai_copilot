.PHONY: help setup migrate up down logs web-build dbt-run seed-demo test clean db-check dev-api tunnel-6543 tunnel-5432 demo

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Set up the development environment
	@echo "Setting up Level Analyst development environment..."
	cp .env.example .env
	@echo "✓ Created .env file from template"
	@echo ""
	@echo "⚠️  IMPORTANT: Edit .env and add your Supabase database URL:"
	@echo "   SUPABASE_DB_URL=postgres://ai_analyst_copilot:YOUR_PASSWORD@db.xzokblkebghmqargqgjb.supabase.co:5432/postgres"
	@echo ""

migrate: ## Run database migrations
	@echo "Running database migrations..."
	@if [ -z "$$SUPABASE_DB_URL" ]; then \
		echo "❌ SUPABASE_DB_URL not set. Run 'make setup' and edit .env first."; \
		exit 1; \
	fi
	@echo "Applying migration 0001_core.sql..."
	psql "$$SUPABASE_DB_URL" -f migrations/0001_core.sql
	@echo "Applying migration 0002_rls_policies.sql..."
	psql "$$SUPABASE_DB_URL" -f migrations/0002_rls_policies.sql
	@echo "Applying migration 0003_elasticity_probe.sql..."
	psql "$$SUPABASE_DB_URL" -f migrations/0003_elasticity_probe.sql
	@echo "✓ Database migrations completed"

up: ## Start the services
	@echo "Starting Level Analyst services..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Services available at:"
	@echo "  API: http://localhost:$${API_PORT:-8088}"
	@echo "  Card: http://localhost:$${API_PORT:-8088}/card"
	@echo ""

down: ## Stop the services
	@echo "Stopping Level Analyst services..."
	docker-compose down
	@echo "✓ Services stopped"

logs: ## Show service logs
	docker-compose logs -f analyst-api

web-build: ## Build the web card and copy to static directory
	@echo "Building web card..."
	cd web/card && npm install && npm run build
	@echo "✓ Web card built and copied to services/analyst/static/iframe/"

web-package: ## Produce standalone frontend artifact (dist/ + dist.tar.gz)
	@echo "Building distributable web artifact..."
	cd web/card && npm install && npm run build:artifact
	@echo "✓ Frontend artifact created at web/card/dist.tar.gz"

dbt-run: ## Run dbt models to create analytics tables
	@echo "Running dbt models..."
	@if [ -z "$$SUPABASE_DB_URL" ]; then \
		echo "❌ SUPABASE_DB_URL not set. Run 'make setup' and edit .env first."; \
		exit 1; \
	fi
	cd analytics && dbt run --profiles-dir .
	@echo "✓ dbt models executed"

seed-insights: ## Seed the database with demo insights
	@echo "Seeding demo insights..."
	@if [ -z "$$SUPABASE_DB_URL" ]; then \
		echo "❌ SUPABASE_DB_URL not set. Run 'make setup' and edit .env first."; \
		exit 1; \
	fi
	@echo "Creating demo insights..."
	psql "$$SUPABASE_DB_URL" -c "INSERT INTO insights (zone_id, kind, narrative_text, confidence) VALUES ('z-110', 'performance', 'Occupancy has increased 15% over the last week, indicating strong demand during morning hours.', 0.82), ('z-221', 'alert', 'Revenue per space has dropped 8% compared to last month. Consider rate optimization.', 0.74);"
	@echo "✓ Demo insights seeded"

test: ## Run tests
	@echo "Running tests..."
	cd services/analyst && python -m pytest tests/ -v
	@echo "✓ Tests completed"

db-check: ## Run database connectivity diagnostics
	@echo "Running database connectivity check..."
	@python3 scripts/db-check.py

dev-api: ## Start FastAPI development server (no Docker)
	@echo "Starting FastAPI development server..."
	cd services/analyst && python3 -m uvicorn analyst.main:app --reload --host 0.0.0.0 --port 8080

clean: ## Clean up build artifacts
	@echo "Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	rm -rf services/analyst/static/iframe/*
	rm -rf web/card/dist/
	rm -rf web/card/node_modules/
	@echo "✓ Cleanup completed"

# Elasticity probe targets
probe-schedule: ## Schedule an elasticity probe (usage: make probe-schedule ZONE=z-110 DAYPART=evening DOW=1 DELTAS=-0.05,0.02,0.05)
	@echo "Scheduling elasticity probe..."
	@if [ -z "$(ZONE)" ]; then echo "❌ ZONE parameter required"; exit 1; fi
	@if [ -z "$(DAYPART)" ]; then echo "❌ DAYPART parameter required (morning|evening)"; exit 1; fi
	@if [ -z "$(DOW)" ]; then echo "❌ DOW parameter required (0-6)"; exit 1; fi
	@python3 scripts/probe_schedule.py $(ZONE) $(DAYPART) $(DOW) $(if $(DELTAS),--deltas=$(DELTAS)) $(if $(HORIZON),--horizon=$(HORIZON))

probe-list: ## List elasticity probe experiments
	@echo "Listing elasticity probe experiments..."
	@python3 scripts/probe_list.py $(if $(ZONE),--zone=$(ZONE)) $(if $(STATUS),--status=$(STATUS)) $(if $(LIMIT),--limit=$(LIMIT))

probe-evaluate: ## Evaluate elasticity probe experiment (usage: make probe-evaluate EXPERIMENT_ID=<uuid>)
	@echo "Evaluating elasticity probe experiment..."
	@if [ -z "$(EXPERIMENT_ID)" ]; then echo "❌ EXPERIMENT_ID parameter required"; exit 1; fi
	@python3 scripts/probe_evaluate.py $(EXPERIMENT_ID)

probe-demo: ## Schedule a demo elasticity probe for zone z-110
	@echo "Scheduling demo elasticity probe..."
	@python3 scripts/probe_schedule.py z-110 evening 1 --deltas=-0.05,0.02,0.05 --horizon=14
	@echo ""
	@echo "💡 Next steps:"
	@echo "  1. List experiments: make probe-list"
	@echo "  2. View details via API: curl http://localhost:8080/experiments/"
	@echo "  3. Evaluate results: make probe-evaluate EXPERIMENT_ID=<uuid>"

# Development shortcuts
dev: setup migrate dbt-run seed-demo up ## Full development setup
	@echo ""
	@echo "🎉 Level Analyst is ready for development!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Generate a dev token: ./scripts/dev_token.sh"
	@echo "  2. Test the API: ./scripts/gen_recs.sh z-110"
	@echo "  3. Open the card: http://localhost:$${API_PORT:-8088}/card"

tunnel-6543: ## Create SSH tunnel to Supabase pooler (port 6543)
	@echo "Creating SSH tunnel to Supabase pooler..."
	TUNNEL_HOST=${TUNNEL_HOST} TUNNEL_USER=${TUNNEL_USER} TUNNEL_KEY=${TUNNEL_KEY} bash scripts/pg_tunnel.sh 6543

tunnel-5432: ## Create SSH tunnel to Supabase direct (port 5432)
	@echo "Creating SSH tunnel to Supabase direct..."
	TUNNEL_HOST=${TUNNEL_HOST} TUNNEL_USER=${TUNNEL_USER} TUNNEL_KEY=${TUNNEL_KEY} bash scripts/pg_tunnel.sh 5432

seed-demo: ## Seed database with demo transaction data and run dbt
	@echo "Seeding demo data..."
	bash scripts/seed_demo.sh

demo: ## Full demo: seed data + generate recommendations + show next steps
	@echo "Running full demo workflow..."
	bash scripts/quick_demo.sh

prod-build: ## Build for production
	@echo "Building for production..."
	docker-compose build
	make web-build
	@echo "✓ Production build completed"
