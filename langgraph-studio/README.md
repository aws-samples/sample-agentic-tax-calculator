# Agentic Tax Calculator - LangGraph Studio Demo

Multi-agent tax calculation system for Canadian small businesses,
built with LangGraph + Amazon Bedrock.

## Architecture

```
User Query ("Calculate taxes for BIZ001")
    │
    ▼
┌─────────────────────┐
│   Tax Supervisor     │  ← Routes to agents in order
└─────────┬───────────┘
          │
    ┌─────┼─────────────────────┐
    ▼     ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│Business││Income  ││Expense ││Asset   ││Tax     │
│Agent   ││Agent   ││Agent   ││Agent   ││Agent   │
└───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
  Tools     Tools     Tools     Tools     Tools
  (MCP)     (MCP)     (MCP)     (MCP)   (Engine)
```

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Tax Supervisor** | Orchestrates the workflow | Routes to sub-agents |
| **Business Agent** | Retrieves business metadata | `get_business_info`, `list_businesses` |
| **Income Agent** | Fetches revenue data | `get_income` |
| **Expense Agent** | Fetches expense data | `get_expenses` |
| **Asset Agent** | Fetches HST/GST data | `get_assets` |
| **Tax Agent** | Computes tax liability | `calculate_tax`, `get_supported_jurisdictions` |

## Prerequisites

- Python 3.11+
- AWS credentials configured (`aws configure` or environment variables)
- Amazon Bedrock model access enabled for Claude Sonnet in your account
- See `.env.example` for configuration options

## Quick Start

```bash
# From this directory
cp .env.example .env        # then edit .env with your region/model
pip install -e .
langgraph dev
```

Open: https://smith.langchain.com/studio/thread?baseUrl=http://127.0.0.1:2024

## Test Prompts

- "Calculate taxes for BIZ001" (Ontario consulting firm, $217K revenue)
- "What businesses are available?"
- "Calculate taxes for BIZ002" (BC design studio, $107K revenue)
- "Calculate taxes for BIZ003" (Alberta tech firm, $388K revenue)

## Mock Data to Production

Tools currently use mock data. In production, they would call
the MCP server which fronts the accounting GraphQL API:

```
Mock: get_business_info("BIZ001") -> BUSINESSES["BIZ001"]
Prod: get_business_info("BIZ001") -> MCP Server -> GraphQL API
```

## Connection to Production Architecture

This demo maps 1:1 to the production design:
- **LangGraph** for orchestration
- **AgentCore Runtime** for deployment
- **Token passthrough** auth
- **DynamoDB** for memory/checkpointing
- **MCP server** fronting the accounting GraphQL API
