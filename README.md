# Agentic Tax Calculator

> **Reuse Note:** This starter kit is customer-agnostic. All source code in `src/`, configuration, agents, tax engine, guardrails, and MCP server contain no customer-specific references.
>
> Mock data in `src/mock/data/*.json` uses fictional business names and can be used as-is or replaced with your own test data.

Agentic Canadian tax calculator - an AWS AgentCore starter kit.

## Overview

A configurable reference implementation that uses multi-agent LangGraph orchestration
backed by AWS AgentCore services to gather business data via MCP tool groups, then
deterministically compute federal, provincial, CPP, and EI tax liabilities for
Canadian small businesses across all 13 provinces and territories.

The system works **out of the box with mock data** - no external credentials needed.
Swap to real services by changing environment variables only.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for AgentCore CLI)
- **AWS CLI v2** (for CDK deployment)
- **Docker** (optional, for local DynamoDB and container builds)

## Installation

```bash
# Clone and install
cd agentic-tax-calculator
pip install -e ".[dev]"
```

## Running with Mock Data

No credentials required. The system uses built-in mock data by default.

```bash
# Option 1: Interactive demo UI (recommended for first look)
pip install -e ".[demo]"
streamlit run demo_ui.py

# Option 2: Run the MCP server directly
python mcp_server.py

# Option 3: Run via the unified entry point
python -m src.app

# Option 4: Run a quick tax calculation via CLI
python -m src.api.cli
```

> **Demo UI:** The Streamlit demo shows the full system - form + chat UX, live guardrails, observability hooks, and architecture config. See [DEMO_QUICKSTART.md](DEMO_QUICKSTART.md) for local, Docker, and AWS deployment options.

### Run Tests

```bash
pytest
```
## Configuration

All settings are controlled via `TAX_CALC_` prefixed environment variables.
Create a `.env` file or export them directly.

| Variable | Default | Description |
|----------|---------|-------------|
| `TAX_CALC_DEPLOYMENT_MODE` | `agentcore` | `agentcore` or `kubernetes` |
| `TAX_CALC_DATA_SOURCE_MODE` | `mock` | `mock` or `graphql` |
| `TAX_CALC_GRAPHQL_ENDPOINT` | _(empty)_ | GraphQL API URL (required when mode=graphql) |
| `TAX_CALC_OKTA_DOMAIN` | _(empty)_ | Okta domain for OAuth 2.0 |
| `TAX_CALC_OKTA_CLIENT_ID` | _(empty)_ | Okta client ID |
| `TAX_CALC_OKTA_CLIENT_SECRET` | _(empty)_ | Okta client secret |
| `TAX_CALC_DYNAMODB_TABLE_NAME` | `tax-calc-shared-state` | DynamoDB table for workflow state |
| `TAX_CALC_MEMORY_TABLE_NAME` | `tax-calc-memory` | DynamoDB table for long-term memory |
| `TAX_CALC_MEMORY_RETENTION_DAYS` | `90` | Long-term memory retention |
| `TAX_CALC_AWS_REGION` | `us-east-1` | AWS region |
| `TAX_CALC_LOG_LEVEL` | `INFO` | Logging level |
| `TAX_CALC_LLM_MODEL_ID` | `anthropic.claude-sonnet-4-6-20250514` | Bedrock model ID |
| `TAX_CALC_DATADOG_API_KEY` | _(empty)_ | DataDog API key for metrics forwarding |

See `src/config/settings.py` for the full list.

### Switching to Real Services

```bash
# Point to your GraphQL API
export TAX_CALC_DATA_SOURCE_MODE=graphql
export TAX_CALC_GRAPHQL_ENDPOINT=<your-graphql-endpoint>

# Configure Okta auth
export TAX_CALC_OKTA_DOMAIN=<your-okta-domain>
export TAX_CALC_OKTA_CLIENT_ID=your-client-id
export TAX_CALC_OKTA_CLIENT_SECRET=your-client-secret
```

### Running with the Local GraphQL Server (Integration Testing)

A local mock GraphQL server is included for testing the full integration plumbing
without needing access to a production API. It serves the same data as the JSON
mock files but through a real GraphQL endpoint.

```bash
# Terminal 1: Start the local GraphQL server
pip install -e ".[dev]"
python graphql_server.py
# Server at http://localhost:8090/graphql
# GraphiQL playground available in browser at same URL

# Terminal 2: Run integration tests
python tests/test_graphql_integration.py

# Terminal 2 (alternative): Run the MCP server in GraphQL mode
TAX_CALC_DATA_SOURCE_MODE=graphql TAX_CALC_GRAPHQL_ENDPOINT=http://localhost:8090/graphql python mcp_server.py
```

This validates the full chain: MCP tools -> GraphQLDataProvider -> GraphQLClient -> HTTP -> GraphQL server -> response mapping. When ready for production, swap the endpoint URL to your real API and update `src/graphql/queries.py` to match your schema.

## AgentCore Deployment

### 1. Install AgentCore CLI

```bash
npm install -g @aws/agentcore
```

### 2. Create the AgentCore project

```bash
agentcore create --protocol MCP
```

### 3. Deploy supporting infrastructure (DynamoDB + IAM)

```bash
cd infra
cdk deploy --app "python cdk_app.py"
```

### 4. Add gateway with Okta JWT auth

```bash
agentcore add gateway \
  --name TaxCalcGateway \
  --authorizer-type CUSTOM_JWT \
  --discovery-url https://<okta-domain>/oauth2/default/.well-known/openid-configuration \
  --runtimes agentic-tax-calculator
```

### 5. Add memory with strategies

```bash
agentcore add memory \
  --name tax-calc-memory \
  --strategies SUMMARIZATION,USER_PREFERENCE
```

### 6. Deploy to AgentCore

```bash
agentcore deploy
```

## Kubernetes Deployment

### Local Development with Docker Compose

```bash
# Start MCP server + DynamoDB Local
docker compose up -d

# Server available at http://localhost:8000
# DynamoDB Local at http://localhost:8001
```

### Helm Chart Deployment

```bash
# Deploy to existing K8s cluster
helm install tax-calc ./infra/helm \
  --set image.repository=your-ecr-repo/agentic-tax-calculator \
  --set image.tag=latest \
  --set config.dataSourceMode=graphql \
  --set auth.oktaDomain=<your-okta-domain>

# Upgrade
helm upgrade tax-calc ./infra/helm --set image.tag=v1.1.0
```

### Build Container Image

```bash
docker build -t agentic-tax-calculator:latest .
```

## Architecture

### Request Flow

```
AI Client → AgentCore Identity (OAuth 2.0 / Okta)
          → AgentCore Gateway
          → AgentCore Runtime
          → PII Pre-filter (Guardrails)
          → LangGraph Orchestrator
              Phase 1: Business Agent → get_business_info
              Phase 2: Income Agent   → get_income     (parallel)
                       Expense Agent  → get_expenses   (parallel)
                       Asset Agent    → get_assets     (parallel)
              Phase 3: Tax Agent      → calculate_tax + validate
          → Tax Post-validation (Guardrails)
          → Response
```

### Agent Workflow

1. **Business Agent** - retrieves business metadata (accounting method, jurisdiction)
2. **Income Agent** - queries CREDIT accounts, calculates total revenue
3. **Expense Agent** - queries DEBIT accounts, calculates total expenses
4. **Asset Agent** - queries HST/GST tax account data
5. **Tax Agent** - aggregates all data, invokes deterministic tax engine, validates result

### MCP Tools

| Tool | Description |
|------|-------------|
| `get_business_info` | Business metadata (accounting method, jurisdiction) |
| `get_income` | P&L CREDIT accounts and total revenue |
| `get_expenses` | P&L DEBIT accounts and total expenses |
| `get_assets` | HST/GST tax account data |
| `calculate_tax` | Deterministic Canadian tax computation |
| `get_tax_rules` | CRA bracket rules for any jurisdiction |

## Project Structure

```
agentic-tax-calculator/
├── agentcore/
│   └── agentcore.json          # AgentCore deployment config
├── infra/
│   ├── cdk_app.py              # CDK stack (DynamoDB + IAM)
│   └── helm/                   # Kubernetes Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── src/
│   ├── app.py                  # Unified entry point (mode switching)
│   ├── config/                 # Pydantic settings + env vars
│   ├── agents/                 # 5 LangGraph agents
│   ├── orchestrator/           # LangGraph workflow + DynamoDB checkpointer
│   ├── mcp/                    # FastMCP server + 6 tool modules
│   ├── graphql/                # GraphQL client + provider + query definitions
│   ├── tax_engine/             # Deterministic Canadian tax engine
│   ├── validation/             # Post-validation engine
│   ├── guardrails/             # PII filter + access control
│   ├── memory/                 # Short-term + long-term memory
│   ├── auth/                   # Okta OAuth 2.0 client
│   ├── observability/          # OpenTelemetry metrics + DataDog/Streamlit hooks
│   ├── mock/                   # Mock data layer (JSON files)
│   └── api/                    # Request handler + schemas
├── tests/
│   └── test_graphql_integration.py  # GraphQL integration tests
├── mcp_server.py               # AgentCore entry point
├── graphql_server.py           # Local mock GraphQL server (for testing)
├── demo_ui.py                  # Streamlit demo UI (5 tabs)
├── Dockerfile
├── Dockerfile.demo             # Demo UI container
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt            # Runtime deps for AgentCore
├── DEMO_QUICKSTART.md          # Demo deployment guide
└── DEPLOYMENT_GUIDE.md         # Full production deployment reference
```

## Supported Jurisdictions

All 13 Canadian provinces and territories:
AB, BC, MB, NB, NL, NS, NT, NU, ON, PE, QC, SK, YT

## Phase 2 (Planned)

- Bank Transaction PDF Import (Textract + Claude 3.5)
- US Tax Support (IRS federal + state brackets)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
