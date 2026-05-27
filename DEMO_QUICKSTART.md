# Demo Quickstart - Agentic Tax Calculator

This guide walks you through deploying the Agentic Tax Calculator using the full AWS AgentCore platform. The deployment uses:

| AgentCore Service | What It Does in This Project |
|---|---|
| **AgentCore Runtime** | Hosts the MCP server in a serverless microVM with session isolation |
| **AgentCore Gateway** | Routes MCP tool calls with JWT auth and semantic search |
| **AgentCore Identity** | Authenticates users via Okta/Cognito JWT tokens |
| **AgentCore Memory** | Short-term session events + long-term semantic retrieval |
| **AgentCore Observability** | CloudWatch traces, logs, and OTEL metrics (automatic) |

---

## Option A: Run Locally First (No AWS Needed)

Try it with mock data before deploying to AWS.

```bash
cd agentic-tax-calculator
pip install -e ".[demo]"

# Run the Streamlit demo UI
streamlit run demo_ui.py

# Or run a quick CLI calculation
python -m src.api.cli --business-id BIZ001 --tax-year 2024
```

Opens at `http://localhost:8501`. No credentials required.

---

## Option B: Deploy to AWS with AgentCore

### Prerequisites

- **Node.js 20+** - `node --version`
- **Python 3.11+** - `python --version`
- **AWS CLI v2** - `aws sts get-caller-identity`
- **IAM permissions** - [AgentCore CLI Permissions](https://github.com/aws/agentcore-cli/blob/main/docs/PERMISSIONS.md)

### Step 1: Install the AgentCore CLI

```bash
npm install -g @aws/agentcore
agentcore --version
```

### Step 2: Set Up Authentication

AgentCore Runtime requires an identity provider for secure access. You can use Cognito (quickest for demo) or Okta (production).

**Option: Cognito (Quick Demo Setup)**

```bash
export REGION=us-east-1
export USERNAME=demo-user
export PASSWORD=YourPassword123!

# Create user pool + client + user
aws cognito-idp create-user-pool \
  --pool-name "TaxCalcDemoPool" \
  --policies '{"PasswordPolicy":{"MinimumLength":8}}' \
  --region $REGION > /tmp/pool.json

export POOL_ID=$(cat /tmp/pool.json | python -c "import sys,json; print(json.load(sys.stdin)['UserPool']['Id'])")

aws cognito-idp create-user-pool-client \
  --user-pool-id $POOL_ID \
  --client-name "TaxCalcClient" \
  --no-generate-secret \
  --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" \
  --region $REGION > /tmp/client.json

export CLIENT_ID=$(cat /tmp/client.json | python -c "import sys,json; print(json.load(sys.stdin)['UserPoolClient']['ClientId'])")

aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username $USERNAME \
  --region $REGION \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username $USERNAME \
  --password $PASSWORD \
  --region $REGION \
  --permanent

# Get bearer token for testing
export BEARER_TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD \
  --region $REGION | python -c "import sys,json; print(json.load(sys.stdin)['AuthenticationResult']['AccessToken'])")

export DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$POOL_ID/.well-known/openid-configuration"

echo "Discovery URL: $DISCOVERY_URL"
echo "Bearer Token saved to BEARER_TOKEN env var"
```

**Option: Okta (Production)**

```bash
export DISCOVERY_URL="https://<your-okta-domain>/oauth2/default/.well-known/openid-configuration"
# Get a bearer token from your Okta app
```

### Step 3: Create the AgentCore Project

```bash
cd agentic-tax-calculator

# Scaffold the AgentCore project
# When prompted: select MCP protocol, Python, Bedrock model provider
agentcore create --protocol MCP --name AgenticTaxCalculator
```

This generates the `agentcore/` directory with `agentcore.json` and `aws-targets.json`. The project already includes a pre-configured `agentcore.json` - the CLI may overwrite it, so verify the config after creation.

### Step 4: Add AgentCore Gateway (Tool Routing + Auth)

The Gateway makes your MCP tools discoverable and adds JWT authentication.

```bash
# Add gateway with JWT auth pointing to your identity provider
agentcore add gateway \
  --name TaxCalcGateway \
  --authorizer-type CUSTOM_JWT \
  --discovery-url "$DISCOVERY_URL" \
  --runtimes agentic-tax-calculator

# Add the MCP server as a gateway target
agentcore add gateway-target \
  --gateway TaxCalcGateway \
  --runtime agentic-tax-calculator
```

What this gives you:
- All 6 MCP tools (`get_business_info`, `get_income`, `get_expenses`, `get_assets`, `calculate_tax`, `get_tax_rules`) are exposed through the Gateway
- JWT tokens are validated on every request
- Semantic search lets agents discover tools by description

### Step 5: Add AgentCore Memory

```bash
agentcore add memory \
  --name tax-calc-memory \
  --strategies SEMANTIC,SUMMARIZATION,USER_PREFERENCE
```

What this gives you:
- **Short-term**: Session events via `CreateEvent` / `ListEvents` (used by `src/memory/short_term.py`)
- **Long-term**: Semantic retrieval via `RetrieveMemoryRecords` (used by `src/memory/long_term.py`)
- **Extraction strategies**: SEMANTIC extracts key facts, SUMMARIZATION condenses sessions, USER_PREFERENCE learns defaults

### Step 6: Deploy

```bash
agentcore deploy
```

This will:
1. Package the Python code + `requirements.txt`
2. Upload to S3
3. Create an AgentCore Runtime (serverless microVM)
4. Provision the Gateway endpoint
5. Create the Memory store
6. Configure CloudWatch observability (automatic)

After deployment, you'll get a Runtime ARN:
```
arn:aws:bedrock-agentcore:us-east-1:<ACCOUNT_ID>:runtime/agentic-tax-calculator-xyz123
```

### Step 7: Verify Deployment

```bash
# Check status of all resources
agentcore status

# Stream logs
agentcore logs

# View traces
agentcore traces list
```

### Step 8: Test the Deployed MCP Server

**Option A: MCP Inspector (Visual)**

```bash
# Install and launch the MCP Inspector
npx @modelcontextprotocol/inspector
```

In the browser at `http://localhost:6274`:
1. Select "Streamable HTTP" transport
2. Enter the endpoint URL (URL-encode the ARN):
   ```
   https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/<ENCODED_ARN>/invocations?qualifier=DEFAULT
   ```
3. Add Authorization header: `Bearer <YOUR_BEARER_TOKEN>`
4. Click Connect - you'll see all 6 tools listed
5. Click any tool to test it (e.g., `get_business_info` with `business_id=BIZ001`, `tax_year=2024`)

**Option B: Python MCP Client**

```python
import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    agent_arn = os.getenv("AGENT_ARN")
    token = os.getenv("BEARER_TOKEN")

    encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
    url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    headers = {"authorization": f"Bearer {token}"}

    async with streamablehttp_client(url, headers, timeout=120, terminate_on_close=False) as (
        read, write, _
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List all tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # Call a tool
            result = await session.call_tool(
                "get_business_info",
                {"business_id": "BIZ001", "tax_year": 2024},
            )
            print(result)

asyncio.run(main())
```

**Option C: Streamlit Demo UI (pointed at deployed backend)**

The demo UI can also run against the deployed AgentCore backend. Set the environment variables and run:

```bash
export TAX_CALC_DEPLOYMENT_MODE=agentcore
export TAX_CALC_AWS_REGION=us-east-1
streamlit run demo_ui.py
```

---

## What's Running on AgentCore

After deployment, here's what each AgentCore service is doing:

```
┌─────────────────────────────────────────────────────────────┐
│  AI Client (Copilot / Kiro / Streamlit Demo / Custom)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  AgentCore Gateway (TaxCalcGateway)                          │
│  • JWT validation via Cognito/Okta                           │
│  • Semantic tool discovery                                   │
│  • Routes MCP tool calls to Runtime                          │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  AgentCore Runtime (serverless microVM)                      │
│  • Hosts mcp_server.py (FastMCP, streamable-http)            │
│  • Session isolation per user                                │
│  • Auto-scaling, consumption-based pricing                   │
│  • 6 MCP tools registered                                   │
│                                                              │
│  Inside the Runtime:                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PII Pre-filter → LangGraph Orchestrator               │  │
│  │    Phase 1: Business Agent → get_business_info         │  │
│  │    Phase 2: Income | Expense | Asset (parallel)        │  │
│  │    Phase 3: Tax Agent → calculate_tax + validate       │  │
│  │  → Post-validation → Response                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────┬───────────────────────────────────┬───────────────┘
           │                                   │
           ▼                                   ▼
┌─────────────────────┐          ┌──────────────────────────────┐
│  AgentCore Memory   │          │  AgentCore Observability      │
│  • CreateEvent      │          │  • CloudWatch Logs (auto)     │
│  • ListEvents       │          │  • X-Ray Traces (auto)        │
│  • RetrieveRecords  │          │  • OTEL metrics (auto)        │
│  • SEMANTIC strategy│          │  • Per-tool latency/errors    │
│  • SUMMARIZATION    │          │  • Workflow duration           │
│  • USER_PREFERENCE  │          └──────────────────────────────┘
└─────────────────────┘
```

---

## AgentCore Services → Code Mapping

| AgentCore Service | Code File | What It Does |
|---|---|---|
| Runtime | `mcp_server.py` | FastMCP entry point, hosted in microVM |
| Gateway | `agentcore/agentcore.json` | Config for JWT auth + tool routing |
| Identity | `src/auth/identity.py` | Okta OAuth 2.0 client (client-credentials + on-behalf-of) |
| Memory (short-term) | `src/memory/short_term.py` | `boto3.client("bedrock-agentcore")` → `create_event`, `list_events` |
| Memory (long-term) | `src/memory/long_term.py` | `boto3.client("bedrock-agentcore-control")` → `create_memory`, `retrieve_memory_records` |
| Observability | `src/observability/metrics.py` | OpenTelemetry counters, histograms, traces (ADOT auto-instrumented) |
| Policy/Guardrails | `src/guardrails/access_control.py` | Per-agent tool permissions matrix |
| Policy/Guardrails | `src/guardrails/pii_filter.py` | PII detection/redaction before LLM and memory |

---

## Cleanup

```bash
# Remove all AgentCore resources
agentcore remove all
agentcore deploy

# Remove Cognito (if you created it for demo)
aws cognito-idp delete-user-pool --user-pool-id $POOL_ID --region $REGION
```

---

## Next Steps

- [x] GraphQL integration implemented (`src/graphql/` package + local mock server)
- [ ] Connect to your real GraphQL API (update `src/graphql/queries.py` with your schema)
- [ ] Configure Okta instead of Cognito for production auth
- [ ] Add Cedar policies via AgentCore Policy for fine-grained tool access (same Cedar language as Amazon Verified Permissions, applied to agent-to-tool access)
- [ ] Set up AgentCore Evaluations for automated agent quality testing
- [ ] Enable DataDog export (`TAX_CALC_DATADOG_API_KEY=...`)
