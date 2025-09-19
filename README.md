# Level Analyst

**AI Analyst module for Level Parking** - A production-ready standalone and embeddable system for zone-scoped parking analytics with LLM-powered insights, recommendations, and safe execution capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Level Analyst provides:

- 🧠 **AI-powered insights** and recommendations for parking pricing optimization
- 🔒 **Zone-scoped authentication** with row-level security (RLS)
- 💬 **Interactive discussion threads** for collaborative decision making
- 📊 **Rate inference** from transaction data with tier recommendations
- ⚡ **Embeddable components** (React card + Web Component)
- 🛡️ **Policy guardrails** and safety constraints
- 🔄 **Feedback memory system** for continuous learning
- 📈 **dbt analytics** for data transformation and aggregation

- Observability: OpenTelemetry tracing (optional) and a Prometheus `/metrics` endpoint help monitor runtime health.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database (Supabase recommended)
- Python 3.11+
- Node.js 18+ (for web components)

### Setup

1. **Clone and configure**:
   ```bash
   git clone <repository-url> level-analyst
   cd level-analyst
   make setup
   ```

2. **Edit `.env` with your database URL**:
   ```bash
   # Add your Supabase connection string:
   SUPABASE_DB_URL=postgres://ai_analyst_copilot:YOUR_PASSWORD@db.xzokblkebghmqargqgjb.supabase.co:5432/postgres
   ```

3. **Initialize database and start services**:
   ```bash
   make migrate
   make up
   make web-build
   make seed-demo
   ```

4. **Generate a development token**:
   ```bash
   ./scripts/dev_token.sh > token.txt
   ```

5. **Test the system**:
   ```bash
   # Generate AI recommendations
   ./scripts/gen_recs.sh z-110

   # Open the web interface
   open http://localhost:8088/card
   ```

## Architecture

```
level-analyst/
├── services/analyst/          # FastAPI backend service
│   ├── analyst/
│   │   ├── routes/           # API endpoints
│   │   ├── core/             # Business logic
│   │   ├── models/           # Pydantic models
│   │   └── deps/             # Dependencies (auth, etc.)
│   └── static/               # Static assets
├── analytics/                # dbt data transformation
├── web/card/                 # React web component
├── migrations/               # Database migrations
├── scripts/                  # Utility scripts
└── tests/                    # Test suite
```

## Core Features

### 🧠 AI-Powered Analysis

The system uses OpenAI models to:
- Analyze parking performance data
- Generate pricing recommendations
- Provide contextual insights
- Respond to user questions in discussion threads

**Models used**:
- `gpt-4o-mini` (fast): General analysis and tool use
- `o1-mini` (reasoning): Complex optimization problems

### 🔒 Zone-Scoped Security

Authentication uses JWT tokens with zone-based access control:

```typescript
// JWT Claims Structure
{
  "iss": "app.lvlparking.com",
  "sub": "user-id",
  "org_id": "org-demo",
  "roles": ["viewer", "approver"],
  "zone_ids": ["z-110", "z-221"],  // User's accessible zones
  "exp": 1640995200
}
```

All database queries are automatically filtered by the user's `zone_ids` using PostgreSQL RLS policies.

### 📊 Rate Inference Engine

Automatically infers current pricing tiers from transaction data:

- Analyzes stay duration patterns
- Calculates optimal tier boundaries
- Generates morning/evening rate schedules
- Considers day-of-week variations

### 🛡️ Policy Guardrails

Safety constraints prevent harmful pricing changes:

```json
{
  "max_change_pct": 0.15,           // ±15% maximum change
  "min_price": 2.0,                 // $2.00 minimum rate
  "blackout_weekday_hours": {       // No changes during peak
    "fri": [16, 17, 18, 19]
  },
  "require_approval_if_confidence_lt": 0.7
}
```

### 💭 Memory System

Learns from user feedback through discussion threads:

- **Canonical**: Universal rules ("Always price Friday evenings higher")
- **Context**: Situational insights ("During events, expect 2x demand")
- **Exception**: Notable anomalies ("Zone Z-110 behaves differently in winter")

### 🧪 Elasticity Probe System

Safe A/B testing for pricing optimization with guardrails and statistical rigor:

- **Experiment Design**: Create controlled pricing tests with multiple delta variants
- **Guardrails**: Automatic limits on price changes and approval requirements
- **Zone-Scoped**: All experiments respect user's zone access permissions
- **Lift Metrics**: Revenue per space-hour and occupancy impact measurement
- **Evaluation**: Statistical analysis of experiment results with confidence intervals

**Example experiment**:
```json
{
  "zone_id": "z-110",
  "daypart": "evening",
  "dow": 1,
  "deltas": [-0.05, 0.0, 0.02, 0.05],  // -5%, control, +2%, +5%
  "horizon_days": 14
}
```

**CLI commands**:
```bash
# Schedule a probe experiment
make probe-schedule ZONE=z-110 DAYPART=evening DOW=1 DELTAS=-0.05,0.02,0.05

# List experiments
make probe-list

# Evaluate results
make probe-evaluate EXPERIMENT_ID=uuid
```

### 🎯 Recommendation Engine

Generates actionable pricing recommendations:

```json
{
  "type": "price_adjustment",
  "rationale_text": "High occupancy (82%) indicates pricing power",
  "proposal": {
    "target_daypart": "morning",
    "target_dow": [1,2,3,4,5],
    "price_changes": [
      {
        "tier_description": "First hour",
        "current_rate": 5.00,
        "proposed_rate": 5.50,
        "change_pct": 0.10
      }
    ]
  },
  "expected_lift_json": {
    "revenue_lift_pct": 0.08,
    "occupancy_impact_pct": -0.02
  },
  "confidence": 0.75
}
```

## API Reference

### Authentication

All API endpoints require a Bearer token:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8088/insights"
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/` | GET | Service health check |
| `/insights/` | GET | List insights for accessible zones |
| `/recommendations/` | GET | List recommendations |
| `/recommendations/generate` | POST | Generate new AI recommendations |
| `/changes/` | GET | List price changes |
| `/changes/apply` | POST | Apply a price change |
| `/changes/revert` | POST | Revert a price change |
| `/threads/` | POST | Start discussion thread |
| `/threads/{id}/messages` | POST | Reply to thread |
| `/memories/upsert` | POST | Save feedback as memories |
| `/experiments/elasticity/probe` | POST | Schedule elasticity probe experiment |
| `/experiments/` | GET | List experiments |
| `/experiments/{id}` | GET | Get experiment details |
| `/experiments/{id}/evaluate` | POST | Evaluate experiment results |

### Example Requests

**Generate recommendations:**
```bash
curl -X POST "http://localhost:8088/recommendations/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"zone_id": "z-110", "context": "Focus on weekend optimization"}'
```

**Start a discussion:**
```bash
curl -X POST "http://localhost:8088/threads/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"insight_id": "uuid", "zone_id": "z-110"}'
```

**Schedule elasticity probe:**
```bash
curl -X POST "http://localhost:8088/experiments/elasticity/probe" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "z-110",
    "daypart": "evening",
    "dow": 1,
    "deltas": [-0.05, 0.02, 0.05],
    "horizon_days": 14
  }'
```

## Web Components

### React Card Component

Full-featured analytics interface:

```tsx
import AnalystCard from './AnalystCard'

<AnalystCard
  token="jwt-token"
  zoneId="z-110"
  mode="review"
/>
```

### Web Component

Embeddable in any web application:

```html
<script src="/static/webcomponent/analyst-card.js"></script>

<level-analyst-card
  token="jwt-token"
  zone-id="z-110"
  location-id="uuid"
  mode="execute"
  api-url="http://localhost:8088">
</level-analyst-card>
```

**Events:**
- `applyRequest`: User wants to apply a price change
- `revertRequest`: User wants to revert a change
- `recommendationsRequested`: User requested new recommendations

## Development

### Local Development

```bash
# Full development setup
make dev

# Individual commands
make setup          # Create .env from template
make migrate        # Run database migrations
make up             # Start services
make web-build      # Build React components
make dbt-run        # Run analytics models
make seed-demo      # Add sample data
make test           # Run test suite
```

### Database Schema

Key tables:
- `insights`: AI-generated insights about performance
- `recommendations`: Pricing change suggestions
- `price_changes`: Applied pricing modifications
- `insight_threads`: Discussion threads
- `thread_messages`: Conversation history
- `feedback_memories`: Learned rules and patterns
- `agent_prompt_versions`: AI prompt templates
- `agent_guardrails`: Safety constraints
- `pricing_experiments`: Elasticity probe experiment definitions
- `pricing_experiment_arms`: Individual test variants within experiments
- `pricing_experiment_results`: Computed lift metrics and statistical results

### Authentication Modes

**Development (HS256)**:
```bash
# Generate dev token (30 min expiry)
./scripts/dev_token.sh > token.txt
```

**Production (RS256)**:
```bash
# Set JWT public key for validation
export JWT_PUBLIC_KEY_BASE64="base64-encoded-public-key"
```

### Testing

```bash
# Run all tests
make test

# Run specific test files
cd services/analyst
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_guardrails.py -v
python -m pytest tests/test_rate_inference.py -v
```

## Deployment

### Production Build

```bash
make prod-build
```

### Environment Variables

Required for production:

```bash
# Database
SUPABASE_DB_URL=postgres://ai_analyst_copilot:password@host:5432/db

# Authentication
JWT_ISSUER=app.lvlparking.com
JWT_PUBLIC_KEY_BASE64=base64-encoded-rsa-public-key

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Server
API_PORT=8088
CORS_ALLOW_ORIGINS=https://app.lvlparking.com

# Feature flags
ANALYST_AUTO_APPLY=false
ANALYST_REQUIRE_APPROVAL=true

# Elasticity probe settings
ANALYST_ENABLE_ELASTICITY_PROBE=true
ANALYST_PROBE_MAX_DELTA=0.10
ANALYST_PROBE_DEFAULT_DELTAS="[-0.05,-0.02,0.02,0.05]"
ANALYST_PROBE_HORIZON_DAYS=14
```

### Security Considerations

1. **Never commit secrets**: Use `.env` files and environment variables
2. **Rotate API keys**: OpenAI key should be rotated before production
3. **Use RS256 JWTs**: Replace HS256 with asymmetric signing
4. **Database permissions**: Use dedicated `ai_analyst_copilot` role
5. **CORS configuration**: Restrict to known domains
6. **Rate limiting**: Add API rate limits in production
7. **Audit logging**: Log all price changes and applications

## Utility Scripts

All scripts support help text with `-h` or `--help`:

```bash
# Generate development JWT token
./scripts/dev_token.sh [zone_ids] [expiry_minutes]

# Generate AI recommendations
./scripts/gen_recs.sh <zone_id> [context] [token]

# Start discussion thread
./scripts/thread_start.sh <insight_id> <zone_id> [token]

# Reply to thread
./scripts/thread_reply.sh <thread_id> <message> [token]

# Apply price change
./scripts/apply.sh <change_id> [force] [token]

# Revert price change
./scripts/revert.sh <change_id> [reason] [token]

# Schedule elasticity probe experiment
./scripts/probe_schedule.py <zone_id> <daypart> <dow> [--deltas=...] [--horizon=14]

# List probe experiments
./scripts/probe_list.py [--zone=z-110] [--status=scheduled]

# Evaluate probe experiment results
./scripts/probe_evaluate.py <experiment_id>
```

## Integration Guide

### Webhook Integration

Add webhook URLs to receive notifications:

```javascript
// Listen for web component events
document.addEventListener('applyRequest', (event) => {
  const { changeId, zoneId } = event.detail

  // Send to external system (Slack, n8n, etc.)
  fetch('/webhook/notify', {
    method: 'POST',
    body: JSON.stringify({
      type: 'price_change_request',
      changeId,
      zoneId
    })
  })
})
```

### External Rates API

When available, configure external pricing integration:

```bash
RATES_API_BASE_URL=https://rates.yourdomain.com
RATES_API_TOKEN=your-api-token
```

The system will automatically sync applied changes to the external API.

### Data Pipeline Integration

Connect your transaction data:

1. **Replace synthetic data** in `analytics/models/staging/stg_transactions.sql`
2. **Add real occupancy data** in `analytics/models/staging/stg_occupancy.sql`
3. **Run dbt models**: `make dbt-run`
4. **Schedule periodic runs** for fresh analytics

## Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Verify connection string
psql "$SUPABASE_DB_URL" -c "SELECT 1"

# Check RLS policies are applied
make migrate
```

**JWT token expired:**
```bash
# Generate new token
./scripts/dev_token.sh > token.txt
```

**OpenAI API errors:**
```bash
# Check API key is valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**Web component not loading:**
```bash
# Rebuild and restart
make web-build
make up
```

### Logs and Debugging

```bash
# View service logs
make logs

# Check health endpoints
curl http://localhost:8088/health/
curl http://localhost:8088/health/db
```

## Roadmap

### Current Version (v0.1.0)
- ✅ Core API with zone-scoped auth
- ✅ AI insights and recommendations
- ✅ Interactive discussion threads
- ✅ Policy guardrails and safety
- ✅ Rate inference from transaction data
- ✅ Web components (React + vanilla JS)
- ✅ dbt analytics pipeline

### Planned Features (v0.2.0)
- [ ] Advanced ML models for demand forecasting
- [ ] Multi-tenant organization support
- [ ] Real-time pricing adjustments
- [ ] Advanced visualization dashboards
- [ ] Slack/Teams integration
- [ ] Mobile-responsive UI improvements

### Future Enhancements (v1.0.0)
- [ ] Multi-language support
- [ ] Advanced A/B testing framework
- [ ] Integration with parking hardware systems
- [ ] Predictive maintenance insights
- [ ] Carbon footprint optimization

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `make test`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide
- Add tests for new features
- Update documentation for API changes
- Use conventional commit messages
- Test with multiple zone configurations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Network Bypass Options

If both 5432 and 6543 time out from your network/VPN, try one of the following:

### Option A: SSH Tunnel (fast)
Requires any reachable Linux VM you control.
```bash
# In terminal A (keeps tunnel open)
TUNNEL_HOST=your.vm.example.com TUNNEL_USER=ubuntu ./scripts/pg_tunnel.sh 6543

# In terminal B (override env while tunnel is active)
cp .env.tunnel.example .env.tunnel
# edit .env.tunnel to insert YOUR_PASSWORD
export $(grep -v '^#' .env.tunnel | xargs)

# Start the API
uvicorn analyst.main:app --host 0.0.0.0 --port 8080 --reload
```

### Option B: GitHub Codespaces (zero setup)
For corporate networks that block everything:
```bash
# Push repo to GitHub → "Code" → "Create codespace on main"
# In the codespace terminal:
echo 'SUPABASE_DB_URL=postgresql://ai_analyst_copilot:YOUR_PASSWORD@db.xzokblkebghmqargqgjb.supabase.co:6543/postgres?sslmode=require' > .env
cd services/analyst && uvicorn analyst.main:app --host 0.0.0.0 --port 8080 --reload
```

See [docs/CLOUD_DEV.md](docs/CLOUD_DEV.md) for full Codespaces guide.

## Demo: seed data → generate recs

### Quick demo (local or via SSH tunnel/Codespaces)
1) Ensure SUPABASE_DB_URL is set (use pooler 6543 + sslmode=require, or run your SSH tunnel and use 127.0.0.1:15432).
2) Seed and build:
   ```bash
   make seed-demo
   ```
   This loads 80 synthetic transactions across zones z-110/z-221, creates staging tables, and runs dbt transformations.

3) Generate recommendations and explore:
   ```bash
   make demo
   ```
   This runs the full workflow: seed → generate AI recommendations → show API endpoints.

4) Explore the results:
   - **API docs**: http://localhost:8080/docs
   - **Web interface**: http://localhost:8080/card/
   - **Raw recommendations**: `curl -H "Authorization: Bearer dev-token" http://localhost:8080/recommendations/`

**Data included**: 10 days of transactions (Sept 8-18, 2025) with realistic pricing tiers, morning/evening patterns, and zone-specific demand characteristics.

## Support

- 📧 **Email**: engineering@lvlparking.com
- 💬 **Slack**: #level-analyst (internal)
- 🐛 **Issues**: GitHub Issues tab
- 📖 **Docs**: This README and inline code documentation

---

Built with ❤️ by the Level Parking team
## Deployment

- [Production Deployment Guide](docs/production-deployment.md) – Details on the Gunicorn/nginx stack and runtime configuration.
- [Frontend Deployment Guide](docs/frontend-deployment.md) – Packaging workflow and CDN publishing tips.
- [Security Hardening Checklist](docs/security-hardening.md) – Recommendations for secrets, TLS, dependency scanning, and monitoring.
- [Continuous Integration](docs/ci-cd.md) – CI jobs, local reproduction steps, and audit guidance.

## Testing

Run the automated test suite after installing the backend with development extras:

```bash
cd services/analyst
pip install -e .[dev]
python -m pytest ../../tests -v
```

Tests cover the background scheduler, daily refresh orchestration, and other core behaviors. Ensure network access is available when installing dependencies.
